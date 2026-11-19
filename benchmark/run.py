"""Compare matching workloads and record fetch-all latency."""
import argparse
from collections import Counter
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import statistics
import time

from bson import json_util
import mysql.connector
from pymongo import MongoClient

from indexes import MONGO_INDEXES, MONGO_URI


def find_command(collection, criteria, fields):
    return {
        'find': collection,
        'filter': criteria,
        'projection': {'_id': 0, **dict.fromkeys(fields, 1)},
    }


def aggregate_command(collection, pipeline):
    return {'aggregate': collection, 'pipeline': pipeline, 'cursor': {}}


CASES = (
    (
        'filter',
        'SELECT product_id,name,price FROM products WHERE price > 500',
        find_command('products', {'price': {'$gt': 500}}, ('product_id', 'name', 'price')),
        ('product_id', 'name', 'price'),
    ),
    (
        'join',
        'SELECT o.order_id,c.name,o.order_date FROM orders o '
        'JOIN customers c ON o.customer_id=c.customer_id',
        aggregate_command('orders', [
            {'$lookup': {
                'from': 'customers', 'localField': 'customer_id',
                'foreignField': 'customer_id', 'as': 'customer',
            }},
            {'$unwind': '$customer'},
            {'$project': {'_id': 0, 'order_id': 1, 'name': '$customer.name', 'order_date': 1}},
        ]),
        ('order_id', 'name', 'order_date'),
    ),
    (
        'aggregation',
        'SELECT customer_id,SUM(total_amount) AS revenue FROM orders GROUP BY customer_id',
        aggregate_command('orders', [{'$group': {'_id': '$customer_id', 'revenue': {'$sum': '$total_amount'}}}]),
        ('_id', 'revenue'),
    ),
    (
        'customer_filter',
        'SELECT order_id,customer_id,order_date,total_amount FROM orders WHERE customer_id = 100',
        find_command('orders', {'customer_id': 100}, ('order_id', 'customer_id', 'order_date', 'total_amount')),
        ('order_id', 'customer_id', 'order_date', 'total_amount'),
    ),
)


def mysql_fetch(connection, sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def mongo_fetch(database, command):
    if 'find' in command:
        collection = database[command['find']]
        return list(collection.find(command['filter'], command['projection']))
    return list(database[command['aggregate']].aggregate(command['pipeline']))


def normalize(value):
    if isinstance(value, datetime) and value == datetime.combine(value.date(), datetime.min.time()):
        return value.date()
    if isinstance(value, float):
        return Decimal(str(value))
    return value


def check_results(name, mysql_rows, mongo_rows, fields):
    if len(mysql_rows) != len(mongo_rows):
        raise RuntimeError(f'{name}: MySQL={len(mysql_rows)} rows, MongoDB={len(mongo_rows)} rows')
    remaining = Counter(tuple(map(normalize, row)) for row in mysql_rows)
    for document in mongo_rows:
        row = tuple(normalize(document[field]) for field in fields)
        if remaining[row] == 0:
            raise RuntimeError(f'{name}: unmatched MongoDB row {row!r}')
        remaining[row] -= 1
    return len(mysql_rows)


def read_mongo_indexes(database, phase):
    indexes = {}
    for name in ('products', 'customers', 'orders'):
        indexes[name] = list(database[name].list_indexes())
        expected = {'_id_': {'_id': 1}}
        if phase == 'indexed' and name in MONGO_INDEXES:
            expected[MONGO_INDEXES[name]] = {'customer_id': 1}
        actual = {index['name']: dict(index['key']) for index in indexes[name]}
        if actual != expected:
            step = 'benchmark/setup.py' if phase == 'baseline' else 'benchmark/indexes.py after a clean setup'
            raise RuntimeError(f'{name}: unexpected indexes for {phase}: {actual}. Check {step}.')
    return indexes


def benchmark(connection, database, args):
    mongo_indexes = read_mongo_indexes(database, args.phase)
    records = []
    for name, sql, command, fields in CASES:
        expected_count = check_results(
            name, mysql_fetch(connection, sql), mongo_fetch(database, command), fields,
        )
        print(f'{name}: verified {expected_count} rows in both systems', flush=True)
        for dbms, fetch in (
            ('MySQL', lambda: mysql_fetch(connection, sql)),
            ('MongoDB', lambda: mongo_fetch(database, command)),
        ):
            for _ in range(args.warmups):
                fetch()
            times = []
            for iteration in range(1, args.runs + 1):
                start = time.perf_counter_ns()
                count = len(fetch())
                elapsed = (time.perf_counter_ns() - start) / 1e6
                if count != expected_count:
                    raise RuntimeError(f'{name}/{dbms}: expected {expected_count} rows, got {count}')
                times.append(elapsed)
                records.append((name, dbms, iteration, f'{elapsed:.4f}', count))
            print(f'  {dbms:8} median={statistics.median(times):.2f} ms', flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', newline='', encoding='utf-8') as output:
        writer = csv.writer(output)
        writer.writerow(('query', 'dbms', 'iteration', 'time_ms', 'row_count'))
        writer.writerows(records)
    print(f'Saved {args.out}')
    if args.plans:
        save_plans(connection, database, args, mongo_indexes)


def save_plans(connection, database, args, mongo_indexes):
    def mysql_indexes(table):
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f'SHOW INDEX FROM {table}')
            return cursor.fetchall()

    evidence = {
        'phase': args.phase,
        'runs': args.runs,
        'warmups': args.warmups,
        'mysql_version': mysql_fetch(connection, 'SELECT VERSION()')[0][0],
        'mongodb_version': database.command('buildInfo')['version'],
        'dataset_counts': {
            table: {
                'MySQL': mysql_fetch(connection, f'SELECT COUNT(*) FROM {table}')[0][0],
                'MongoDB': database[table].count_documents({}),
            }
            for table in ('customers', 'products', 'orders', 'order_items')
        },
        'mysql_indexes': {table: mysql_indexes(table) for table in ('products', 'customers', 'orders')},
        'mongodb_indexes': mongo_indexes,
        'queries': {},
    }
    for name, sql, command, _ in CASES:
        explain = mysql_fetch(connection, 'EXPLAIN ANALYZE FORMAT=TREE ' + sql)
        evidence['queries'][name] = {
            'mysql_sql': sql,
            'mysql_explain_analyze': '\n'.join(row[0] for row in explain),
            'mongodb_explain': database.command('explain', command, verbosity='executionStats'),
        }
    args.plans.parent.mkdir(parents=True, exist_ok=True)
    args.plans.write_text(json_util.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(f'Saved {args.plans}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('baseline', 'indexed'), default='baseline')
    parser.add_argument('--runs', type=int, default=30)
    parser.add_argument('--warmups', type=int, default=5)
    parser.add_argument('--out', type=Path, default=Path('results.csv'))
    parser.add_argument('--plans', type=Path, help='Optional JSON output for plans and experiment metadata')
    args = parser.parse_args()
    if args.runs < 1 or args.warmups < 0:
        parser.error('--runs must be positive and --warmups must be nonnegative')
    if args.plans and args.plans.resolve() == args.out.resolve():
        parser.error('--plans and --out must use different paths')

    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) as client:
        with mysql.connector.connect(
            host='127.0.0.1', user='root', password='rootpass',
            database='ecommerce', connection_timeout=5,
        ) as connection:
            benchmark(connection, client.ecommerce, args)


if __name__ == '__main__':
    main()
