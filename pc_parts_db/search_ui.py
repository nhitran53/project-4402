"""Menu option 1: product search."""
import catalog
from db import UserError, ask, ask_float, ask_int, ask_required, menu, table


def run(con, user):
    def search():
        kw = ask_required("Search for (any words: name, brand, model, category, e.g. 'asus 4070')")
        catalog.search_products(con, kw)

    def browse():
        table(con.execute(
            "SELECT c.category_id AS id, c.name, c.description, COUNT(p.product_id) AS products "
            "FROM categories c LEFT JOIN products p ON p.category_id = c.category_id "
            "GROUP BY c.category_id ORDER BY c.category_id"))
        cat = ask_int("Category id (blank = all)", blank_ok=True)
        top = ask_float("Only products whose lowest in-stock price is at most (blank = any)", blank_ok=True)
        s = ask("Sort by (p)rice low to high, price (h)igh to low, or (n)ame", "p").lower()[:1]
        order = {"p": "bp.best_price ASC", "h": "bp.best_price DESC", "n": "p.name"}.get(s, "bp.best_price ASC")
        where, params = ["1=1"], []
        if cat is not None:
            where.append("p.category_id = ?")
            params.append(cat)
        if top is not None:
            where.append("bp.best_price <= ?")
            params.append(top)
        catalog.list_products(con, " AND ".join(where), params, order)

    def details():
        catalog.show_product(con, catalog.ask_product(con)["product_id"])

    menu(f"Product Search - {user['username']}", [
        ("Search by name, brand or category", search),
        ("Browse a category (filter by price)", browse),
        ("View a product's details and store prices", details),
    ], back_label="Back to main menu")
