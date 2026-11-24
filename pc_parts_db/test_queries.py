#!/usr/bin/env python3
"""
Runs the 5 queries in queries.sql and prints the results.
Run with: python test_queries.py  (or give a different .db file as an argument)
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_queries(path):
    """Split queries.sql into (title, description, sql) blocks. Each starts with '-- Qn: title'."""
    blocks, cur = [], None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"--\s*(Q\d+):\s*(.*)", line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2).strip(), "sql": []}
            blocks.append(cur)
        elif cur is not None:
            cur["sql"].append(line)
    return [(b["id"], b["title"], "".join(b["sql"]).strip()) for b in blocks]


def print_table(cols, rows):
    cells = [[("" if v is None else str(v)) for v in r] for r in rows]
    widths = [max([len(c)] + [len(r[i]) for r in cells]) for i, c in enumerate(cols)]
    line = "  ".join(c.ljust(w) for c, w in zip(cols, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for r in cells:
        print("  ".join(v.ljust(w) for v, w in zip(r, widths)))


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pcparts.db")
    if not os.path.exists(db):
        sys.exit(f"Database {db} not found. Run:  python3 generate_data.py")
    con = sqlite3.connect(db)
    failures = 0
    for qid, title, sql in load_queries(os.path.join(HERE, "queries.sql")):
        print("=" * 100)
        print(f"{qid}: {title}")
        print("=" * 100)
        try:
            cur = con.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            print_table(cols, rows)
            print(f"({len(rows)} rows)\n")
            if not rows:
                failures += 1
        except sqlite3.Error as e:
            failures += 1
            print("ERROR:", e, "\n")
    print("ALL TEST QUERIES PASSED" if failures == 0 else f"{failures} QUERY(IES) FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
