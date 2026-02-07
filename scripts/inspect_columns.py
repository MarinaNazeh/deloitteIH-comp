"""Inspect merged_complete CSV columns. Run: python scripts/inspect_columns.py"""
import csv
import os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(base, "merged_complete_part1.csv")
with open(path, "r", encoding="utf-8") as f:
    r = csv.reader(f)
    header = next(r)
    out = os.path.join(base, "docs", "merged_columns.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as w:
        w.write("Total columns: %d\n\n" % len(header))
        for i, col in enumerate(header):
            w.write("%d\t%s\n" % (i, col))
    print("Total columns:", len(header))
    print("Wrote", out)
