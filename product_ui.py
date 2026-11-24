"""Menu option 3: product management (admin only)."""
import sqlite3

import catalog
from db import (UserError, ask, ask_choice, ask_float, ask_int, ask_required, confirm, menu, table, tx)

TABLE = {"CPU": "cpu", "Motherboard": "motherboard", "RAM": "ram", "GPU": "gpu", "PSU": "psu",
         "Case": "pc_case", "Storage": "storage", "Cooler": "cooler"}
# (column, kind, extra)  kind: int | float | text | choice | lookup
SPEC_FIELDS = {
    "CPU": [("socket_id", "lookup", "socket"), ("cores", "int", None), ("threads", "int", None),
            ("base_ghz", "float", None), ("boost_ghz", "float", None), ("tdp_w", "int", None)],
    "Motherboard": [("socket_id", "lookup", "socket"), ("form_factor_id", "lookup", "form_factor"),
                    ("chipset", "text", None), ("ram_type", "choice", ["DDR4", "DDR5"]),
                    ("ram_slots", "int", None), ("max_ram_gb", "int", None),
                    ("m2_slots", "int", None), ("sata_ports", "int", None)],
    "RAM": [("ram_type", "choice", ["DDR4", "DDR5"]), ("capacity_gb", "int", None),
            ("modules", "int", None), ("speed_mhz", "int", None)],
    "GPU": [("chipset", "text", None), ("vram_gb", "int", None), ("length_mm", "int", None),
            ("tdp_w", "int", None), ("min_psu_w", "int", None)],
    "PSU": [("wattage", "int", None), ("efficiency", "text", None), ("modular", "choice", ["Full", "Semi", "No"])],
    "Case": [("max_gpu_length_mm", "int", None), ("max_cooler_height_mm", "int", None)],
    "Storage": [("storage_type", "choice", ["NVMe SSD", "SATA SSD", "HDD"]), ("capacity_gb", "int", None)],
    "Cooler": [("cooler_type", "choice", ["Air", "Liquid"]), ("height_mm", "int", None), ("max_tdp_w", "int", None)],
}




def run(con, admin):
    def pick_product():
        return catalog.ask_product(con, blank_ok=True)

    def lookup(tbl):
        rows = con.execute(f"SELECT * FROM {tbl} ORDER BY 1").fetchall()
        table(rows)
        v = ask_int(f"Pick a {tbl.replace('_', ' ')} id")
        if v not in {r[0] for r in rows}:
            raise UserError("Not a valid id.")
        return v

    def list_products():
        table(con.execute("SELECT category_id AS id, name FROM categories ORDER BY category_id"))
        cid = ask_int("Category id (blank = all)", blank_ok=True)
        if cid is None:
            catalog.list_products(con, "1=1")
        else:
            catalog.list_products(con, "p.category_id = ?", (cid,))

    def view():
        p = pick_product()
        if p:
            catalog.show_product(con, p["product_id"])

    def add_product():
        cats = con.execute("SELECT category_id AS id, name FROM categories ORDER BY category_id").fetchall()
        table(cats)
        cat_id = ask_int("Category id")
        cat = next((c for c in cats if c["id"] == cat_id), None)
        if cat is None:
            raise UserError("Unknown category.")
        cname = cat["name"]
        brand = ask_required("Brand")
        model = ask_required("Model")
        summary = ask("Short specification text (optional)")
        specs = {}
        for col, kind, extra in SPEC_FIELDS[cname]:
            label = col.replace("_id", "").replace("_", " ")
            if kind == "int":
                specs[col] = ask_int(label, lo=0)
            elif kind == "float":
                specs[col] = ask_float(label, lo=0)
            elif kind == "text":
                specs[col] = ask_required(label)
            elif kind == "choice":
                specs[col] = ask_choice(label, extra)
            else:
                specs[col] = lookup(extra)
        links = []
        if cname == "Case":
            print("  Which motherboard sizes fit?")
            while True:
                links.append(lookup("form_factor"))
                if not confirm("Add another size?"):
                    break
        if cname == "Cooler":
            print("  Which CPU sockets does it mount on?")
            while True:
                links.append(lookup("socket"))
                if not confirm("Add another socket?"):
                    break
        with tx(con):
            pid = con.execute("INSERT INTO products(category_id, name, brand, model, specification) VALUES (?,?,?,?,?)",
                              (cat_id, f"{brand} {model}", brand, model, summary or None)).lastrowid
            cols = ["product_id"] + list(specs)
            con.execute(f"INSERT INTO {TABLE[cname]}({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                        [pid] + list(specs.values()))
            link_tbl = {"Case": ("case_form_factor", "form_factor_id"), "Cooler": ("cooler_socket", "socket_id")}
            if cname in link_tbl:
                t, c = link_tbl[cname]
                for v in set(links):
                    con.execute(f"INSERT INTO {t}(product_id, {c}) VALUES (?,?)", (pid, v))
        print(f"  Added product {pid}: {brand} {model}. Create listings for it in the Listing Management screen.")

    def edit():
        p = pick_product()
        if not p:
            return
        print("  Press Enter to keep a value.")
        brand = ask_required("Brand", p["brand"])
        model = ask_required("Model", p["model"])
        spec = ask("Specification text", p["specification"] or "")
        con.execute("UPDATE products SET brand = ?, model = ?, name = ?, specification = ? WHERE product_id = ?",
                    (brand, model, f"{brand} {model}", spec or None, p["product_id"]))
        print("  Product updated.")

    def delete():
        p = pick_product()
        if p and confirm(f"Permanently delete '{p['name']}'?"):
            try:
                con.execute("DELETE FROM products WHERE product_id = ?", (p["product_id"],))
                print("  Deleted.")
            except sqlite3.IntegrityError:
                raise UserError("This product still has store listings or appears in builds. "
                                "Delete those first, then try again.")

    menu(f"Product Management - {admin['username']} (admin)", [
        ("List products", list_products),
        ("View one product", view),
        ("Add a product (with its technical specifications)", add_product),
        ("Edit a product", edit),
        ("Delete a product", delete),
    ], back_label="Back to main menu")
