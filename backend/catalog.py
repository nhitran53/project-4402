"""Product lookup, price and build-checking functions shared by the screens."""
import difflib
import re

from db import UserError, ask, money, table

# Category -> SQL that returns the technical specifications of one product (parameter: product_id)
SPEC_SQL = {
    "CPU": "SELECT s.name AS socket, x.cores, x.threads, x.base_ghz, x.boost_ghz, x.tdp_w "
           "FROM cpu x JOIN socket s ON s.socket_id = x.socket_id WHERE x.product_id = ?",
    "Motherboard": "SELECT s.name AS socket, f.name AS form_factor, x.chipset, x.ram_type, x.ram_slots, "
                   "x.max_ram_gb, x.m2_slots, x.sata_ports FROM motherboard x "
                   "JOIN socket s ON s.socket_id = x.socket_id "
                   "JOIN form_factor f ON f.form_factor_id = x.form_factor_id WHERE x.product_id = ?",
    "RAM": "SELECT ram_type, capacity_gb, modules, speed_mhz FROM ram WHERE product_id = ?",
    "GPU": "SELECT chipset, vram_gb, length_mm, tdp_w, min_psu_w FROM gpu WHERE product_id = ?",
    "PSU": "SELECT wattage, efficiency, modular FROM psu WHERE product_id = ?",
    "Case": "SELECT x.max_gpu_length_mm, x.max_cooler_height_mm, "
            "(SELECT group_concat(f.name, ', ') FROM case_form_factor cf "
            " JOIN form_factor f ON f.form_factor_id = cf.form_factor_id WHERE cf.product_id = x.product_id) "
            "AS form_factors FROM pc_case x WHERE x.product_id = ?",
    "Storage": "SELECT storage_type, capacity_gb FROM storage WHERE product_id = ?",
    "Cooler": "SELECT x.cooler_type, x.height_mm, x.max_tdp_w, "
              "(SELECT group_concat(s.name, ', ') FROM cooler_socket cs "
              " JOIN socket s ON s.socket_id = cs.socket_id WHERE cs.product_id = x.product_id) AS sockets "
              "FROM cooler x WHERE x.product_id = ?",
}

LIST_SQL = ("SELECT p.product_id AS id, p.name, c.name AS category, "
            "(SELECT COUNT(*) FROM listings l WHERE l.product_id = p.product_id) AS stores, "
            "bp.best_price AS lowest_in_stock, bp.store AS cheapest_at "
            "FROM products p JOIN categories c ON c.category_id = p.category_id "
            "LEFT JOIN v_best_price bp ON bp.product_id = p.product_id ")


def list_products(con, where="1=1", params=(), order="c.category_id, p.name"):
    rows = con.execute(f"{LIST_SQL} WHERE {where} ORDER BY {order}", params).fetchall()
    table(rows)
    return rows


def _norm(s):
    """Lower-case and drop spaces/punctuation, so '4070ti', '4070 Ti' and '4070-TI' all compare equal."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def find_products(con, text):
    """Product ids matching free text. Every word must appear (in any order) in the name, brand, model,
    category or summary. If nothing matches exactly, close spellings are accepted (typos).
    Returns (ids, fuzzy) where fuzzy is True when the typo-tolerant pass was needed."""
    tokens = [t for t in (_norm(w) for w in text.split()) if t]
    if not tokens:
        return [], False
    prods = []
    for r in con.execute("SELECT p.product_id, p.name, p.brand, p.model, p.specification, c.name AS category "
                         "FROM products p JOIN categories c ON c.category_id = p.category_id"):
        fields = [r["name"], r["brand"], r["model"], r["specification"], r["category"]]
        words = {_norm(w) for f in fields for w in re.split(r"[\s,/()]+", f or "") if _norm(w)}
        prods.append((r["product_id"], _norm(" ".join(f or "" for f in fields)), words))

    exact = [pid for pid, hay, _ in prods if all(t in hay for t in tokens)]
    if exact:
        return exact, False

    def close(t, hay, words):
        return t in hay or bool(difflib.get_close_matches(t, words, n=1, cutoff=0.75))
    return [pid for pid, hay, words in prods if all(close(t, hay, words) for t in tokens)], True


def search_products(con, text):
    """Print every product matching free text. Returns the rows shown."""
    ids, fuzzy = find_products(con, text)
    if not ids:
        print(f"  No products match '{text}'. Try fewer or shorter words, e.g. a brand or model number.")
        return []
    if fuzzy:
        print(f"  No exact match for '{text}'; showing close spellings:")
    return list_products(con, f"p.product_id IN ({','.join('?' * len(ids))})", ids)


def ask_product(con, prompt="Product (id or part of its name)", blank_ok=False):
    """Ask for a product by id OR by name words. One match is picked directly; several are listed so
    the user can type the id or more words. Returns the product row, or None on blank if blank_ok."""
    while True:
        s = ask(prompt + (" (blank = cancel)" if blank_ok and "blank" not in prompt else ""))
        if not s:
            if blank_ok:
                return None
            print("  This field is required.")
            continue
        if s.isdigit():
            p = get_product(con, int(s))
            if p is not None:
                return p
        ids, fuzzy = find_products(con, s)
        if len(ids) == 1:
            p = get_product(con, ids[0])
            print(f"  -> {p['name']} (product {p['product_id']})")
            return p
        if not search_products(con, s):
            continue
        print("  Several products match: type the id of the one you want, or a more specific name.")


def get_product(con, product_id):
    return con.execute("SELECT p.*, c.name AS category FROM products p "
                       "JOIN categories c ON c.category_id = p.category_id WHERE p.product_id = ?",
                       (product_id,)).fetchone()


def price_table(con, product_id):
    """All store listings of one product, cheapest first, with the best in-stock offer marked."""
    rows = con.execute(
        "SELECT s.name AS store, l.price, l.availability, l.last_updated AS updated, "
        "CASE WHEN l.listing_id = bp.listing_id THEN '<< best price' ELSE '' END AS note, l.product_url AS url "
        "FROM listings l JOIN stores s ON s.store_id = l.store_id "
        "LEFT JOIN v_best_price bp ON bp.product_id = l.product_id "
        "WHERE l.product_id = ? ORDER BY l.price", (product_id,)).fetchall()
    table(rows)
    return rows


def show_product(con, product_id, with_prices=True):
    p = get_product(con, product_id)
    if p is None:
        raise UserError(f"No product with id {product_id}.")
    print(f"\n  {p['name']}   (product {p['product_id']})")
    print(f"  Category: {p['category']}   Brand: {p['brand']}   Model: {p['model']}")
    print(f"  Summary: {p['specification'] or '-'}")
    spec = con.execute(SPEC_SQL[p["category"]], (product_id,)).fetchone()
    if spec:
        print("  Technical specifications:")
        for k in spec.keys():
            print(f"    {k.replace('_', ' '):<22}{spec[k]}")
    if with_prices:
        print("\n  Prices:")
        price_table(con, product_id)
    return p


# build compatibility
def build_errors(con, build_id):
    """Set of (rule, message) for every ERROR the compatibility view reports."""
    return {(r["rule"], r["message"]) for r in con.execute(
        "SELECT rule, message FROM v_build_issues WHERE build_id = ? AND severity = 'ERROR'", (build_id,))}


def evaluate_candidates(con, build_id, category_id):
    """For every product of a category that is in stock somewhere, try it in the build (inside a
    transaction that is always rolled back) and report whether it adds any NEW compatibility error.
    Returns [(product_row, is_compatible)]."""
    multi = con.execute("SELECT multi_allowed FROM categories WHERE category_id = ?", (category_id,)).fetchone()[0]
    cands = con.execute("SELECT p.product_id, p.name, bp.best_price AS price, bp.store FROM products p "
                        "JOIN v_best_price bp ON bp.product_id = p.product_id "
                        "WHERE p.category_id = ? ORDER BY bp.best_price", (category_id,)).fetchall()

    def trial(pid):
        con.execute("BEGIN")
        try:
            if not multi:   # a single-slot part would be replaced
                con.execute("DELETE FROM build_items WHERE build_id = ? AND product_id IN "
                            "(SELECT product_id FROM products WHERE category_id = ?)", (build_id, category_id))
            if pid is not None:
                con.execute("INSERT OR IGNORE INTO build_items(build_id, product_id, quantity) VALUES (?,?,1)",
                            (build_id, pid))
            return build_errors(con, build_id)
        finally:
            con.execute("ROLLBACK")

    base = trial(None)
    return [(p, trial(p["product_id"]) <= base) for p in cands]
