#!/usr/bin/env python3
"""
Tests for the compatibility rules, triggers and constraints.
Works on an in-memory copy of pcparts.db, so the real file isn't changed.
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = sqlite3.connect(os.path.join(HERE, "pcparts.db"))
con = sqlite3.connect(":memory:")
src.backup(con)
con.row_factory = sqlite3.Row
con.execute("PRAGMA foreign_keys = ON")

GOOD = {
    "CPU": "AMD Ryzen 7 7800X3D", "MB": "MSI PRO B650-P WIFI",
    "RAM": "Corsair Vengeance 32GB (2x16GB) DDR5-6000", "GPU": "ASUS DUAL GeForce RTX 4060 8GB",
    "PSU": "Corsair RM850x 850W", "CASE": "Corsair 4000D Airflow",
    "COOLER": "Thermalright Peerless Assassin 120 SE", "SSD": "Samsung 990 PRO 1TB NVMe",
}
passed = failed = 0


def pid(name):
    r = con.execute("SELECT product_id FROM products WHERE name = ?", (name,)).fetchone()
    assert r, f"unknown product {name}"
    return r[0]


def make_build(**changes):
    """Build from GOOD parts with some parts replaced; values may be a name, a list of names or (name, qty)."""
    parts = dict(GOOD)
    parts.update(changes)
    cust = con.execute("SELECT user_id FROM users WHERE role='customer' LIMIT 1").fetchone()[0]
    bid = con.execute("INSERT INTO builds(user_id, name) VALUES (?, 'rule test')", (cust,)).lastrowid
    for v in parts.values():
        if v is None:
            continue
        for item in (v if isinstance(v, list) else [v]):
            name, qty = item if isinstance(item, tuple) else (item, 1)
            con.execute("INSERT INTO build_items VALUES (?,?,?)", (bid, pid(name), qty))
    return bid


def rules(bid):
    return {r[0] for r in con.execute("SELECT rule FROM v_build_issues WHERE build_id = ?", (bid,))}


def check(label, ok):
    global passed, failed
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    passed += ok
    failed += (not ok)


print("Compatibility rules")
check("a fully compatible build has no issues", rules(make_build()) == set())
expect = {
    "SOCKET": dict(CPU="Intel Core i5-13600K"),
    "RAM_TYPE": dict(RAM="Corsair Vengeance LPX 16GB (2x8GB) DDR4-3200"),
    "RAM_SLOTS": dict(RAM=("Corsair Vengeance 32GB (2x16GB) DDR5-6000", 3)),
    "RAM_CAPACITY": dict(MB="ASRock B650E PG-ITX WIFI", RAM=("G.Skill Trident Z5 64GB (2x32GB) DDR5-6000", 2)),
    "FORM_FACTOR": dict(CASE="Cooler Master NR200P Mini-ITX"),
    "GPU_LENGTH": dict(GPU="ASUS ROG STRIX GeForce RTX 5090 32GB", CASE="Thermaltake Core V1 Mini-ITX"),
    "COOLER_SOCKET": dict(COOLER="Noctua NH-L9i low-profile"),
    "COOLER_TDP": dict(COOLER="Thermalright AXP90-X53 low-profile"),
    "COOLER_HEIGHT": dict(CASE="Fractal Design Terra Mini-ITX"),
    "PSU_POWER": dict(PSU="Cooler Master MWE 400 Bronze V2 400W"),
    "M2_SLOTS": dict(SSD=["Samsung 990 PRO 1TB NVMe", "WD Black SN850X 1TB NVMe", "Crucial P3 Plus 1TB NVMe"]),
    "SATA_PORTS": dict(SSD=["WD Blue SA510 500GB SATA SSD", "Crucial MX500 1TB SATA SSD",
                            "Samsung 870 EVO 2TB SATA SSD", "Seagate Barracuda 1TB HDD", "Seagate Barracuda 2TB HDD"]),
}
for rule, change in expect.items():
    check(f"{rule} is reported when it should be", rule in rules(make_build(**change)))
check("MISSING warns about an empty case/PSU/etc.", "MISSING" in rules(make_build(PSU=None, CASE=None)))
bid = make_build(PSU=None)
check("MISSING is the only issue when just the PSU is left out", rules(bid) == {"MISSING"})

print("\nTriggers and constraints")


def refused(sql, params=()):
    try:
        con.execute(sql, params)
        return False
    except sqlite3.IntegrityError:
        return True


cpu_id = pid(GOOD["CPU"])
admin = con.execute("SELECT user_id FROM users WHERE role = 'admin' LIMIT 1").fetchone()[0]
customer = con.execute("SELECT user_id FROM users WHERE role = 'customer' LIMIT 1").fetchone()[0]
store = con.execute("SELECT store_id FROM stores ORDER BY store_id LIMIT 1").fetchone()[0]
new_prod = con.execute("INSERT INTO products(category_id, name, brand, model) VALUES (1, 'Test CPU', 'X', 'T1')").lastrowid
INS = ("INSERT INTO listings(product_id, store_id, created_by_user_id, price, availability, last_updated) "
       "VALUES (?,?,?,?,?,datetime('now'))")
check("an admin can create a listing", not refused(INS, (new_prod, store, admin, 99.0, "in_stock")))
check("a customer cannot create a listing", refused(INS, (new_prod, 2, customer, 99.0, "in_stock")))
check("only one listing per product and store", refused(INS, (new_prod, store, admin, 80.0, "in_stock")))
check("negative prices are refused", refused(INS, (new_prod, 3, admin, -1.0, "in_stock")))
check("availability must be a known value", refused(INS, (new_prod, 3, admin, 50.0, "maybe")))
check("a listing needs an existing store", refused(INS, (new_prod, 999, admin, 50.0, "in_stock")))
lid = con.execute("SELECT listing_id FROM listings WHERE product_id = ?", (new_prod,)).fetchone()[0]
con.execute("UPDATE listings SET last_updated = '2000-01-01 00:00:00' WHERE listing_id = ?", (lid,))
con.execute("UPDATE listings SET price = 95 WHERE listing_id = ?", (lid,))
check("changing a price refreshes last_updated", con.execute(
    "SELECT last_updated FROM listings WHERE listing_id = ?", (lid,)).fetchone()[0] > "2020")
check("a store with listings cannot be deleted", refused("DELETE FROM stores WHERE store_id = ?", (store,)))
check("a product with listings cannot be deleted", refused("DELETE FROM products WHERE product_id = ?", (new_prod,)))
check("a category with products cannot be deleted", refused("DELETE FROM categories WHERE category_id = 1"))
check("a GPU spec row cannot be attached to a CPU product",
      refused("INSERT INTO gpu VALUES (?,?,?,?,?,?)", (cpu_id, "x", 8, 200, 100, 500)))
check("a build cannot hold two CPUs", refused(
    "INSERT INTO build_items VALUES (?,?,1)", (make_build(), pid("Intel Core i5-13600K"))))
check("user roles are limited to admin / customer",
      refused("INSERT INTO users(username, email, role) VALUES ('z','z@z','boss')"))
check("v_best_price returns the cheapest in-stock listing", con.execute(
    "SELECT best_price FROM v_best_price WHERE product_id = ?", (new_prod,)).fetchone()[0] == 95)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
