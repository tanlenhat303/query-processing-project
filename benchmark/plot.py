"""Plot median fetch-all latency for the two DBMSs."""
import argparse
from collections import defaultdict
import csv
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('csv', type=Path, nargs='?', default=Path('results.csv'))
parser.add_argument('--out', type=Path, default=Path('comparison.png'))
args = parser.parse_args()

data = defaultdict(list)
with args.csv.open(newline='', encoding='utf-8') as source:
    for row in csv.DictReader(source):
        data[row['query'], row['dbms']].append(float(row['time_ms']))

queries = sorted({query for query, _ in data})
systems = ('MySQL', 'MongoDB')
if not queries or any((query, dbms) not in data for query in queries for dbms in systems):
    parser.error('The CSV must contain results from both databases for each query.')

positions = list(range(len(queries)))
width = 0.36
figure, axes = plt.subplots(figsize=(9, 5))
for offset, dbms in enumerate(systems):
    values = [median(data[query, dbms]) for query in queries]
    axes.bar([x + (offset - 0.5) * width for x in positions], values, width, label=dbms)

axes.set_xticks(positions, queries)
axes.set_ylabel('Median client-side execution time (ms)')
axes.legend()
figure.tight_layout()
args.out.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(args.out, dpi=160)
print(f'Saved {args.out}')
