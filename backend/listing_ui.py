"""Menu option 4: listing management (admin only)."""
import catalog
from db import UserError, ask, ask_choice, ask_float, ask_int, ask_required, confirm, menu, table

AVAIL = ["in_stock", "out_of_stock", "preorder"]


def run(con, admin):
    def show_listing(lid):
        l = con.execute("SELECT l.*, p.name AS product, s.name AS store FROM listings l "
                        "JOIN products p ON p.product_id = l.product_id JOIN stores s ON s.store_id = l.store_id "
                        "WHERE l.listing_id = ?", (lid,)).fetchone()
        if l is None:
            raise UserError(f"No listing {lid}.")
        print(f"\n  Listing {lid}: {l['product']} at {l['store']}  ${l['price']:,.2f}  {l['availability']}")
        print(f"  URL: {l['product_url']}   last updated {l['last_updated']}")
        return l

    def list_listings():
        p = catalog.ask_product(con, "Product id or name (blank = any)", blank_ok=True)
        pid = p["product_id"] if p else None
        sid = ask_int("Store id (blank = any)", blank_ok=True)
        where, params = ["1=1"], []
        if pid is not None:
            where.append("l.product_id = ?")
            params.append(pid)
        if sid is not None:
            where.append("l.store_id = ?")
            params.append(sid)
        table(con.execute(
            "SELECT l.listing_id AS id, p.name AS product, s.name AS store, l.price, l.availability, l.last_updated "
            "FROM listings l JOIN products p ON p.product_id = l.product_id JOIN stores s ON s.store_id = l.store_id "
            f"WHERE {' AND '.join(where)} ORDER BY p.name, l.price LIMIT 25", params))

    def add_listing():
        p = catalog.ask_product(con)
        table(con.execute("SELECT store_id AS id, name, website FROM stores ORDER BY store_id"))
        sid = ask_int("Store id")
        price = ask_float("Price", lo=0)
        av = ask_choice("Availability", AVAIL, "in_stock")
        url = ask("Product URL")
        con.execute("INSERT INTO listings(product_id, store_id, created_by_user_id, price, availability, product_url, "
                    "last_updated) VALUES (?,?,?,?,?,?,datetime('now'))",
                    (p["product_id"], sid, admin["user_id"], price, av, url or None))
        print("  Listing added.")

    def update_listing():
        l = show_listing(ask_int("Listing id"))
        print("  Press Enter to keep a value.")
        price = ask_float("New price", lo=0, default=l["price"])
        av = ask_choice("Availability", AVAIL, l["availability"])
        url = ask("Product URL", l["product_url"] or "")
        con.execute("UPDATE listings SET price = ?, availability = ?, product_url = ? WHERE listing_id = ?",
                    (price, av, url or None, l["listing_id"]))
        print("  Listing updated (timestamp refreshed).")

    def delete_listing():
        l = show_listing(ask_int("Listing id"))
        if confirm("Delete this listing?"):
            con.execute("DELETE FROM listings WHERE listing_id = ?", (l["listing_id"],))
            print("  Listing deleted.")

    def stale():
        days = ask_int("Show listings not updated for at least how many days", lo=0, default=14)
        table(con.execute(
            "SELECT l.listing_id AS id, p.name AS product, s.name AS store, l.price, l.last_updated "
            "FROM listings l JOIN products p ON p.product_id = l.product_id JOIN stores s ON s.store_id = l.store_id "
            "WHERE julianday('now') - julianday(l.last_updated) >= ? ORDER BY l.last_updated LIMIT 20", (days,)))

    menu(f"Listing Management - {admin['username']} (admin)", [
        ("List listings (filter by product / store)", list_listings),
        ("Add a listing", add_listing),
        ("Update price, availability or URL", update_listing),
        ("Delete a listing", delete_listing),
        ("Find out-of-date listings", stale),
    ], back_label="Back to main menu")
