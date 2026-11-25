"""Menu option 2: price comparison and the PC builder."""
import catalog
from db import UserError, ask, ask_int, ask_required, confirm, menu, money, table, tx


def run(con, user):
    uid = user["user_id"]

    # price comparison
    def compare():
        pid = catalog.ask_product(con)["product_id"]
        p = catalog.show_product(con, pid, with_prices=False)
        rows = con.execute("SELECT s.name AS store, l.price, l.availability, l.last_updated AS updated, l.product_url AS url "
                           "FROM listings l JOIN stores s ON s.store_id = l.store_id WHERE l.product_id = ? "
                           "ORDER BY (l.availability <> 'in_stock'), l.price", (pid,)).fetchall()
        print("\n  Store prices (in-stock offers first, cheapest first):")
        table(rows)
        instock = [r["price"] for r in rows if r["availability"] == "in_stock"]
        if len(instock) > 1:
            print(f"  Buying at the cheapest in-stock store saves {money(max(instock) - min(instock))} "
                  f"compared with the most expensive one.")
        elif not instock:
            print("  No store has this product in stock right now.")

    def best_in_category():
        table(con.execute("SELECT category_id AS id, name FROM categories ORDER BY category_id"))
        cid = ask_int("Category id")
        table(con.execute("SELECT p.product_id AS id, p.name, bp.best_price AS lowest_in_stock, bp.store "
                          "FROM products p JOIN v_best_price bp ON bp.product_id = p.product_id "
                          "WHERE p.category_id = ? ORDER BY bp.best_price", (cid,)))

    # builds
    def list_builds():
        table(con.execute(
            "SELECT b.build_id AS id, b.name, b.created_at AS created, t.total_price AS total_at_best_prices, "
            "(SELECT COUNT(*) FROM v_build_issues i WHERE i.build_id = b.build_id AND i.severity = 'ERROR') AS errors, "
            "(SELECT COUNT(*) FROM v_build_issues i WHERE i.build_id = b.build_id AND i.severity = 'WARNING') AS missing "
            "FROM builds b JOIN v_build_total t ON t.build_id = b.build_id "
            "WHERE b.user_id = ? ORDER BY b.build_id", (uid,)))

    def pick_build():
        list_builds()
        bid = ask_int("Build id (blank = cancel)", blank_ok=True)
        if bid is None:
            return None
        b = con.execute("SELECT * FROM builds WHERE build_id = ? AND user_id = ?", (bid, uid)).fetchone()
        if b is None:
            raise UserError("That is not one of your builds.")
        return b

    def show(bid):
        b = con.execute("SELECT * FROM builds WHERE build_id = ?", (bid,)).fetchone()
        print(f"\n  Build #{b['build_id']}: {b['name']}  (created {b['created_at']})")
        table(con.execute(
            "SELECT p.product_id AS id, c.name AS category, p.name, bi.quantity AS qty, bp.best_price AS unit_price, "
            "bp.store AS cheapest_at, ROUND(bi.quantity * bp.best_price, 2) AS line_total "
            "FROM build_items bi JOIN products p ON p.product_id = bi.product_id "
            "JOIN categories c ON c.category_id = p.category_id "
            "LEFT JOIN v_best_price bp ON bp.product_id = p.product_id "
            "WHERE bi.build_id = ? ORDER BY c.category_id", (bid,)))
        t = con.execute("SELECT total_price FROM v_build_total WHERE build_id = ?", (bid,)).fetchone()[0]
        print(f"  Build total at the cheapest in-stock prices: {money(t)}")
        issues = con.execute("SELECT severity, message FROM v_build_issues WHERE build_id = ? ORDER BY severity, rule",
                             (bid,)).fetchall()
        print("\n  Compatibility check:")
        if not issues:
            print("   [OK] Every selected part is compatible and the build is complete.")
        for i in issues:
            print(f"   [{'ERROR' if i['severity'] == 'ERROR' else 'TODO '}] {i['message']}")
        if issues and not any(i["severity"] == "ERROR" for i in issues):
            print("   No compatibility errors.")

    def create():
        bid = con.execute("INSERT INTO builds(user_id, name) VALUES (?,?)",
                          (uid, ask_required("Name for the new build"))).lastrowid
        print(f"  Created build #{bid}. Use 'Add a part' to start filling it.")

    def view():
        b = pick_build()
        if b:
            show(b["build_id"])

    def add_part():
        b = pick_build()
        if not b:
            return
        bid = b["build_id"]
        cats = con.execute("SELECT category_id AS id, name, multi_allowed FROM categories ORDER BY category_id").fetchall()
        table([(c["id"], c["name"], "several allowed" if c["multi_allowed"] else "one per build") for c in cats],
              ["id", "category", "slots"])
        catid = ask_int("Category id")
        cat = next((c for c in cats if c["id"] == catid), None)
        if cat is None:
            raise UserError("Unknown category.")
        print("  Checking every part that is in stock somewhere against your build ...")
        results = catalog.evaluate_candidates(con, bid, catid)
        ok_only = confirm("Show only parts that are compatible with this build?", True)
        shown = [(p, ok) for p, ok in results if ok or not ok_only]
        table([(p["product_id"], p["name"], p["price"], p["store"], "yes" if ok else "NO") for p, ok in shown],
              ["id", "product", "lowest_price", "cheapest_at", "compatible"])
        if not shown:
            return
        pid = ask_int("Product id to add (blank = cancel)", blank_ok=True)
        if pid is None:
            return
        if not any(p["product_id"] == pid for p, _ in results):
            raise UserError("That product is not in the list above.")
        qty = ask_int("Quantity", lo=1, default=1) if cat["multi_allowed"] else 1
        with tx(con):
            if not cat["multi_allowed"]:
                con.execute("DELETE FROM build_items WHERE build_id = ? AND product_id IN "
                            "(SELECT product_id FROM products WHERE category_id = ?)", (bid, catid))
            con.execute("INSERT INTO build_items(build_id, product_id, quantity) VALUES (?,?,?) "
                        "ON CONFLICT(build_id, product_id) DO UPDATE SET quantity = excluded.quantity",
                        (bid, pid, qty))
        print("  Part added.")
        show(bid)

    def remove_part():
        b = pick_build()
        if b:
            show(b["build_id"])
            pid = ask_int("Product id to remove (blank = cancel)", blank_ok=True)
            if pid is not None:
                n = con.execute("DELETE FROM build_items WHERE build_id = ? AND product_id = ?",
                                (b["build_id"], pid)).rowcount
                print("  Removed." if n else "  That part is not in this build.")
                show(b["build_id"])

    def change_qty():
        b = pick_build()
        if b:
            show(b["build_id"])
            pid = ask_int("Product id")
            n = con.execute("UPDATE build_items SET quantity = ? WHERE build_id = ? AND product_id = ?",
                            (ask_int("New quantity", lo=1), b["build_id"], pid)).rowcount
            print("  Updated." if n else "  That part is not in this build.")
            show(b["build_id"])

    def rename():
        b = pick_build()
        if b:
            con.execute("UPDATE builds SET name = ? WHERE build_id = ?",
                        (ask_required("New name", b["name"]), b["build_id"]))
            print("  Renamed.")

    def delete():
        b = pick_build()
        if b and confirm(f"Delete build '{b['name']}' and all its parts?"):
            con.execute("DELETE FROM builds WHERE build_id = ?", (b["build_id"],))
            print("  Build deleted.")

    menu(f"Price Comparison and PC Builder - {user['username']}", [
        ("Compare store prices for a product", compare),
        ("Cheapest in-stock price of every product in a category", best_in_category),
        ("My builds", list_builds),
        ("Start a new build", create),
        ("View a build: total price and compatibility check", view),
        ("Add a part (shows which parts fit)", add_part),
        ("Change the quantity of a part", change_qty),
        ("Remove a part", remove_part),
        ("Rename a build", rename),
        ("Delete a build", delete),
    ], back_label="Back to main menu")
