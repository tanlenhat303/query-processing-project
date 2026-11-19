"""Manage the two MongoDB indexes used in the second measurement."""
from pymongo import MongoClient

MONGO_URI = 'mongodb://127.0.0.1:27017'
MONGO_INDEXES = {
    'customers': 'idx_customers_customer_id',
    'orders': 'idx_orders_customer_id',
}


def add_mongo_indexes(database):
    if set(MONGO_INDEXES).difference(database.list_collection_names()):
        raise RuntimeError('Run benchmark/setup.py before creating indexes.')
    for collection, name in MONGO_INDEXES.items():
        database[collection].create_index([('customer_id', 1)], name=name)
        print(f'{collection}.customer_id: {name}')


if __name__ == '__main__':
    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) as client:
        add_mongo_indexes(client.ecommerce)
