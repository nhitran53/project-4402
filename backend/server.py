#!/usr/bin/env python3
"""Serve the JSON API and the built frontend."""
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import catalog
import db
from product_ui import SPEC_FIELDS, TABLE as SPEC_TABLE

PORT = int(os.environ.get("PORT", "8000"))
DIST_DIR = os.path.realpath(os.path.join(db.HERE, "..", "frontend", "dist"))
AVAILABILITY = ["in_stock", "out_of_stock", "preorder"]

# Login tokens -> user_id. Kept in memory, so restarting the server logs everyone out.
SESSIONS = {}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# Category specifications
#
# For each category: the join that brings in its spec table, and the spec fields as
# (key, label, sql expression, unit, show_in_table, filterable).
# A filterable field gets a checkbox filter in the product browser.
SPEC_JOIN = {
    "CPU": "LEFT JOIN cpu x ON x.product_id = p.product_id "
           "LEFT JOIN socket xs ON xs.socket_id = x.socket_id",
    "Motherboard": "LEFT JOIN motherboard x ON x.product_id = p.product_id "
                   "LEFT JOIN socket xs ON xs.socket_id = x.socket_id "
                   "LEFT JOIN form_factor xf ON xf.form_factor_id = x.form_factor_id",
    "RAM": "LEFT JOIN ram x ON x.product_id = p.product_id",
    "GPU": "LEFT JOIN gpu x ON x.product_id = p.product_id",
    "PSU": "LEFT JOIN psu x ON x.product_id = p.product_id",
    "Case": "LEFT JOIN pc_case x ON x.product_id = p.product_id",
    "Storage": "LEFT JOIN storage x ON x.product_id = p.product_id",
    "Cooler": "LEFT JOIN cooler x ON x.product_id = p.product_id",
}

CASE_FORM_FACTORS = ("(SELECT group_concat(f.name, ', ') FROM case_form_factor cf "
                     "JOIN form_factor f ON f.form_factor_id = cf.form_factor_id "
                     "WHERE cf.product_id = p.product_id)")
COOLER_SOCKETS = ("(SELECT group_concat(s.name, ', ') FROM cooler_socket cs "
                  "JOIN socket s ON s.socket_id = cs.socket_id WHERE cs.product_id = p.product_id)")

SPEC_COLUMNS = {
    "CPU": [("socket", "Socket", "xs.name", "", True, True),
            ("cores", "Core Count", "x.cores", "", True, True),
            ("threads", "Threads", "x.threads", "", False, False),
            ("base_ghz", "Base Clock", "x.base_ghz", "GHz", True, False),
            ("boost_ghz", "Boost Clock", "x.boost_ghz", "GHz", True, False),
            ("tdp_w", "TDP", "x.tdp_w", "W", True, False)],
    "Motherboard": [("socket", "Socket", "xs.name", "", True, True),
                    ("form_factor", "Form Factor", "xf.name", "", True, True),
                    ("chipset", "Chipset", "x.chipset", "", True, True),
                    ("ram_type", "Memory Type", "x.ram_type", "", True, True),
                    ("ram_slots", "Memory Slots", "x.ram_slots", "", False, False),
                    ("max_ram_gb", "Memory Max", "x.max_ram_gb", "GB", True, False),
                    ("m2_slots", "M.2 Slots", "x.m2_slots", "", False, False),
                    ("sata_ports", "SATA Ports", "x.sata_ports", "", False, False)],
    "RAM": [("ram_type", "Type", "x.ram_type", "", True, True),
            ("capacity_gb", "Capacity", "x.capacity_gb", "GB", True, True),
            ("modules", "Modules", "x.modules", "", True, False),
            ("speed_mhz", "Speed", "x.speed_mhz", "MHz", True, True)],
    "GPU": [("chipset", "Chipset", "x.chipset", "", True, True),
            ("vram_gb", "Memory", "x.vram_gb", "GB", True, True),
            ("length_mm", "Length", "x.length_mm", "mm", True, False),
            ("tdp_w", "TDP", "x.tdp_w", "W", True, False),
            ("min_psu_w", "Recommended PSU", "x.min_psu_w", "W", False, False)],
    "PSU": [("wattage", "Wattage", "x.wattage", "W", True, True),
            ("efficiency", "Efficiency Rating", "x.efficiency", "", True, True),
            ("modular", "Modular", "x.modular", "", True, True)],
    "Case": [("form_factors", "Motherboard Support", CASE_FORM_FACTORS, "", True, True),
             ("max_gpu_length_mm", "Max GPU Length", "x.max_gpu_length_mm", "mm", True, False),
             ("max_cooler_height_mm", "Max Cooler Height", "x.max_cooler_height_mm", "mm", True, False)],
    "Storage": [("storage_type", "Type", "x.storage_type", "", True, True),
                ("capacity_gb", "Capacity", "x.capacity_gb", "GB", True, True)],
    "Cooler": [("cooler_type", "Type", "x.cooler_type", "", True, True),
               ("height_mm", "Height", "x.height_mm", "mm", True, False),
               ("max_tdp_w", "Max CPU TDP", "x.max_tdp_w", "W", True, False),
               ("sockets", "Sockets", COOLER_SOCKETS, "", False, True)],
}

# Fields that hold several values per product (N:M link tables) are filtered with EXISTS
# instead of a plain IN, and their filter options are counted from the link table.
MULTI_VALUE_FILTERS = {
    ("Case", "form_factors"): (
        "EXISTS (SELECT 1 FROM case_form_factor cf JOIN form_factor f ON f.form_factor_id = cf.form_factor_id "
        "WHERE cf.product_id = p.product_id AND f.name IN ({}))",
        "SELECT f.name AS value, COUNT(*) AS count FROM case_form_factor cf "
        "JOIN form_factor f ON f.form_factor_id = cf.form_factor_id GROUP BY f.name ORDER BY f.form_factor_id"),
    ("Cooler", "sockets"): (
        "EXISTS (SELECT 1 FROM cooler_socket cs JOIN socket s ON s.socket_id = cs.socket_id "
        "WHERE cs.product_id = p.product_id AND s.name IN ({}))",
        "SELECT s.name AS value, COUNT(*) AS count FROM cooler_socket cs "
        "JOIN socket s ON s.socket_id = cs.socket_id GROUP BY s.name ORDER BY s.name"),
}

# Per-product listing statistics (aggregate over the listings table).
LISTING_STATS = ("LEFT JOIN (SELECT product_id, COUNT(*) AS listing_count, "
                 "SUM(CASE WHEN availability = 'in_stock' THEN 1 ELSE 0 END) AS in_stock_count "
                 "FROM listings GROUP BY product_id) ls ON ls.product_id = p.product_id ")


# Request helpers
ROUTES = []


def route(method, pattern, auth=None):
    """Register a handler. auth: None (public), 'user' (logged in) or 'admin'."""
    def register(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), auth, fn))
        return fn
    return register


class Request:
    def __init__(self, query, body, user):
        self.query = query
        self.body = body
        self.user = user

    def arg(self, name, default=None):
        values = self.query.get(name)
        return values[0].strip() if values and values[0].strip() != "" else default

    def arg_list(self, name):
        values = []
        for v in self.query.get(name, []):
            values.extend(x for x in v.split(",") if x.strip())
        return values

    def arg_int(self, name, default=None, lo=None, hi=None):
        v = self.arg(name)
        if v is None:
            return default
        try:
            n = int(v)
        except ValueError:
            raise ApiError(400, f"'{name}' must be a whole number.")
        if lo is not None:
            n = max(lo, n)
        if hi is not None:
            n = min(hi, n)
        return n

    def arg_float(self, name):
        v = self.arg(name)
        if v is None:
            return None
        try:
            return float(v)
        except ValueError:
            raise ApiError(400, f"'{name}' must be a number.")


def text_field(body, key, label, required=True, max_len=255):
    v = body.get(key)
    v = "" if v is None else str(v).strip()
    if not v:
        if required:
            raise ApiError(400, f"{label} is required.")
        return None
    if len(v) > max_len:
        raise ApiError(400, f"{label} must be at most {max_len} characters.")
    return v


def number_field(body, key, label, integer=False, lo=None):
    v = body.get(key)
    if v is None or str(v).strip() == "":
        raise ApiError(400, f"{label} is required.")
    try:
        n = int(v) if integer else float(v)
    except (TypeError, ValueError):
        raise ApiError(400, f"{label} must be {'a whole number' if integer else 'a number'}.")
    if integer and isinstance(v, float) and v != int(v):
        raise ApiError(400, f"{label} must be a whole number.")
    if lo is not None and n < lo:
        raise ApiError(400, f"{label} cannot be less than {lo}.")
    return n


def paginate(con, sql, params, req, default_size=25):
    page_size = req.arg_int("page_size", default_size, 1, 100)
    total = con.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
    pages = max(1, -(-total // page_size))
    page = req.arg_int("page", 1, 1, pages)
    rows = con.execute(f"{sql} LIMIT ? OFFSET ?", list(params) + [page_size, (page - 1) * page_size]).fetchall()
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size, "pages": pages}


def sort_clause(req, allowed, default):
    """ORDER BY text from ?sort=<key>&dir=asc|desc. Only whitelisted keys reach the SQL."""
    key = req.arg("sort", default)
    if key not in allowed:
        key = default
    direction = "DESC" if req.arg("dir", "asc").lower() == "desc" else "ASC"
    expr = allowed[key]
    # Rows without a value (e.g. no in-stock price) always go last.
    return f"({expr}) IS NULL, {expr} {direction}"


def get_category(con, name):
    row = con.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise ApiError(404, f"Unknown category '{name}'.")
    return row


def friendly_integrity_error(e):
    msg = str(e)
    if "listings.product_id, listings.store_id" in msg:
        return "This store already has a listing for this product. Edit the existing listing instead."
    if "stores.name" in msg:
        return "A store with this name already exists."
    if "users.username" in msg:
        return "That username is already taken."
    if "users.email" in msg:
        return "That e-mail address is already registered."
    if "categories.name" in msg:
        return "A category with this name already exists."
    if msg.startswith("CHECK constraint failed"):
        return "A value breaks a database rule: " + msg.split(":", 1)[-1].strip()
    if msg == "FOREIGN KEY constraint failed":
        return "This record is still referenced by other records, so the database refused the change."
    return msg   # messages raised by our triggers are already readable


def current_user(con, headers):
    auth = headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else None
    user_id = SESSIONS.get(token) if token else None
    if user_id is None:
        return None
    row = con.execute("SELECT user_id, username, email, role FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# Accounts (same username-only login as the terminal app)
def start_session(user):
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = user["user_id"]
    return {"token": token, "user": dict(user)}


@route("POST", "/api/login")
def login(con, req):
    who = text_field(req.body, "username", "Username or e-mail")
    user = con.execute("SELECT user_id, username, email, role FROM users "
                       "WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE", (who, who)).fetchone()
    if user is None:
        raise ApiError(401, "No account with that username or e-mail.")
    return start_session(user)


@route("POST", "/api/register")
def register(con, req):
    username = text_field(req.body, "username", "Username", max_len=50)
    email = text_field(req.body, "email", "E-mail")
    if "@" not in email:
        raise ApiError(400, "Please enter a valid e-mail address.")
    uid = con.execute("INSERT INTO users(username, email, role) VALUES (?, ?, 'customer')",
                      (username, email)).lastrowid
    return start_session(con.execute("SELECT user_id, username, email, role FROM users WHERE user_id = ?",
                                     (uid,)).fetchone())


@route("POST", "/api/logout")
def logout(con, req):
    for token, uid in list(SESSIONS.items()):
        if req.user and uid == req.user["user_id"]:
            SESSIONS.pop(token, None)
    return {"ok": True}


@route("GET", "/api/me")
def me(con, req):
    return {"user": req.user}


# Catalog
@route("GET", "/api/categories")
def categories(con, req):
    rows = con.execute(
        "SELECT c.category_id, c.name, c.description, c.required, c.multi_allowed, "
        "COUNT(p.product_id) AS product_count "
        "FROM categories c LEFT JOIN products p ON p.category_id = c.category_id "
        "GROUP BY c.category_id ORDER BY c.category_id").fetchall()
    return [dict(r) for r in rows]


def product_filters(con, req, category):
    """WHERE conditions and parameters for the product browser."""
    where, params = [], []
    if category:
        where.append("c.name = ?")
        params.append(category)

    search = req.arg("q")
    fuzzy = False
    if search:
        # Re-use the terminal app's word/typo-tolerant search to find matching ids.
        ids, fuzzy = catalog.find_products(con, search)
        if not ids:
            where.append("0")
        else:
            where.append(f"p.product_id IN ({','.join('?' * len(ids))})")
            params.extend(ids)

    brands = req.arg_list("brand")
    if brands:
        where.append(f"p.brand IN ({','.join('?' * len(brands))})")
        params.extend(brands)

    min_price, max_price = req.arg_float("min_price"), req.arg_float("max_price")
    if min_price is not None:
        where.append("bp.best_price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("bp.best_price <= ?")
        params.append(max_price)

    if req.arg("in_stock") == "1":
        where.append("bp.best_price IS NOT NULL")

    stores = [s for s in req.arg_list("store") if s.isdigit()]
    if stores:
        where.append(f"EXISTS (SELECT 1 FROM listings sl WHERE sl.product_id = p.product_id "
                     f"AND sl.store_id IN ({','.join('?' * len(stores))}))")
        params.extend(int(s) for s in stores)

    for key, _, expr, _, _, filterable in SPEC_COLUMNS.get(category, []):
        values = req.arg_list(key)
        if not filterable or not values:
            continue
        marks = ",".join("?" * len(values))
        multi = MULTI_VALUE_FILTERS.get((category, key))
        where.append(multi[0].format(marks) if multi else f"CAST({expr} AS TEXT) IN ({marks})")
        params.extend(values)

    return " AND ".join(where) or "1", params, fuzzy


@route("GET", "/api/products")
def products(con, req):
    category = req.arg("category")
    if category:
        get_category(con, category)
    columns = SPEC_COLUMNS.get(category, [])
    where, params, fuzzy = product_filters(con, req, category)

    spec_select = "".join(f", {expr} AS {key}" for key, _, expr, _, _, _ in columns)
    sql = ("SELECT p.product_id, p.name, p.brand, p.model, p.specification, c.name AS category, c.multi_allowed, "
           "bp.best_price, bp.store AS best_store, "
           "COALESCE(ls.listing_count, 0) AS listing_count, COALESCE(ls.in_stock_count, 0) AS in_stock_count"
           f"{spec_select} "
           "FROM products p JOIN categories c ON c.category_id = p.category_id "
           "LEFT JOIN v_best_price bp ON bp.product_id = p.product_id "
           f"{LISTING_STATS}{SPEC_JOIN.get(category, '')} "
           f"WHERE {where}")

    sortable = {"name": "p.name", "brand": "p.brand", "price": "bp.best_price", "category": "c.category_id"}
    sortable.update({key: expr for key, _, expr, _, _, _ in columns})
    result = paginate(con, f"{sql} ORDER BY {sort_clause(req, sortable, 'price')}, p.name", params, req)
    result["columns"] = [{"key": k, "label": label, "unit": unit}
                         for k, label, _, unit, in_table, _ in columns if in_table]
    result["fuzzy"] = fuzzy
    return result


@route("GET", "/api/products/filters")
def product_filter_options(con, req):
    """Options for the filter sidebar, each with the number of matching products."""
    category = req.arg("category")
    cat_where, params = ("WHERE c.name = ?", [category]) if category else ("", [])
    base = (f"FROM products p JOIN categories c ON c.category_id = p.category_id "
            f"LEFT JOIN v_best_price bp ON bp.product_id = p.product_id {SPEC_JOIN.get(category, '')} {cat_where}")

    brands = con.execute(f"SELECT p.brand AS value, COUNT(*) AS count {base} GROUP BY p.brand ORDER BY p.brand",
                         params).fetchall()
    price = con.execute(f"SELECT MIN(bp.best_price) AS min, MAX(bp.best_price) AS max {base}", params).fetchone()
    stores = con.execute(
        "SELECT s.store_id AS value, s.name AS label, COUNT(DISTINCT l.product_id) AS count "
        "FROM stores s JOIN listings l ON l.store_id = s.store_id "
        "JOIN products p ON p.product_id = l.product_id JOIN categories c ON c.category_id = p.category_id "
        f"{cat_where} GROUP BY s.store_id ORDER BY s.name", params).fetchall()

    specs = []
    for key, label, expr, unit, _, filterable in SPEC_COLUMNS.get(category, []):
        if not filterable:
            continue
        multi = MULTI_VALUE_FILTERS.get((category, key))
        if multi:
            values = con.execute(multi[1]).fetchall()
        else:
            values = con.execute(f"SELECT {expr} AS value, COUNT(*) AS count {base} AND {expr} IS NOT NULL "
                                 f"GROUP BY {expr} ORDER BY {expr}", params).fetchall()
        specs.append({"key": key, "label": label, "unit": unit, "values": [dict(v) for v in values]})

    return {"brands": [dict(b) for b in brands], "stores": [dict(s) for s in stores],
            "price": dict(price), "specs": specs}


def product_or_404(con, product_id):
    row = con.execute("SELECT p.*, c.name AS category, c.multi_allowed FROM products p "
                      "JOIN categories c ON c.category_id = p.category_id WHERE p.product_id = ?",
                      (product_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Product not found.")
    return row


def product_specs(con, product):
    columns = SPEC_COLUMNS.get(product["category"], [])
    if not columns:
        return []
    row = con.execute(f"SELECT {', '.join(f'{expr} AS {key}' for key, _, expr, _, _, _ in columns)} "
                      f"FROM products p {SPEC_JOIN[product['category']]} WHERE p.product_id = ?",
                      (product["product_id"],)).fetchone()
    return [{"key": key, "label": label, "value": row[key], "unit": unit}
            for key, label, _, unit, _, _ in columns if row[key] is not None]


@route("GET", r"/api/products/(\d+)")
def product_detail(con, req, product_id):
    product = product_or_404(con, int(product_id))
    listings = con.execute(
        "SELECT l.listing_id, l.store_id, s.name AS store, l.price, l.availability, l.last_updated, "
        "CASE WHEN l.listing_id = bp.listing_id THEN 1 ELSE 0 END AS is_best "
        "FROM listings l JOIN stores s ON s.store_id = l.store_id "
        "LEFT JOIN v_best_price bp ON bp.product_id = l.product_id "
        "WHERE l.product_id = ? ORDER BY l.availability <> 'in_stock', l.price, s.name",
        (product["product_id"],)).fetchall()
    summary = con.execute(
        "SELECT COUNT(*) AS listing_count, "
        "SUM(CASE WHEN availability = 'in_stock' THEN 1 ELSE 0 END) AS in_stock_count, "
        "MIN(price) AS lowest_price, MAX(price) AS highest_price, ROUND(AVG(price), 2) AS average_price "
        "FROM listings WHERE product_id = ?", (product["product_id"],)).fetchone()
    return {"product": dict(product), "specs": product_specs(con, product),
            "listings": [dict(r) for r in listings], "summary": dict(summary)}


# Stores
STORE_STATS_SQL = (
    "SELECT s.store_id, s.name, s.website, COUNT(l.listing_id) AS listing_count, "
    "COALESCE(SUM(CASE WHEN l.availability = 'in_stock' THEN 1 ELSE 0 END), 0) AS in_stock_count, "
    "(SELECT COUNT(*) FROM v_best_price bp JOIN listings b ON b.listing_id = bp.listing_id "
    " WHERE b.store_id = s.store_id) AS lowest_price_count "
    "FROM stores s LEFT JOIN listings l ON l.store_id = s.store_id ")


@route("GET", "/api/stores")
def stores(con, req):
    return [dict(r) for r in con.execute(STORE_STATS_SQL + "GROUP BY s.store_id ORDER BY s.name")]


@route("GET", r"/api/stores/(\d+)")
def store_detail(con, req, store_id):
    row = con.execute(STORE_STATS_SQL + "WHERE s.store_id = ? GROUP BY s.store_id", (int(store_id),)).fetchone()
    if row is None:
        raise ApiError(404, "Store not found.")
    return dict(row)


@route("GET", r"/api/stores/(\d+)/listings")
def store_listings(con, req, store_id):
    where, params = ["l.store_id = ?"], [int(store_id)]
    if req.arg("category"):
        where.append("c.name = ?")
        params.append(req.arg("category"))
    if req.arg("availability") in AVAILABILITY:
        where.append("l.availability = ?")
        params.append(req.arg("availability"))
    if req.arg("q"):
        where.append("(p.name LIKE ? OR p.brand LIKE ?)")
        params.extend([f"%{req.arg('q')}%"] * 2)
    sql = ("SELECT l.listing_id, l.product_id, p.name AS product, c.name AS category, l.price, l.availability, "
           "l.last_updated, CASE WHEN bp.listing_id = l.listing_id THEN 1 ELSE 0 END AS is_best "
           "FROM listings l JOIN products p ON p.product_id = l.product_id "
           "JOIN categories c ON c.category_id = p.category_id "
           "LEFT JOIN v_best_price bp ON bp.product_id = l.product_id "
           f"WHERE {' AND '.join(where)}")
    sortable = {"product": "p.name", "category": "c.category_id", "price": "l.price",
                "availability": "l.availability", "updated": "l.last_updated"}
    return paginate(con, f"{sql} ORDER BY {sort_clause(req, sortable, 'category')}, p.name", params, req)


# System builder
def clean_build_items(con, raw):
    """Validate [{product_id, quantity, listing_id}] and merge duplicate products."""
    if not isinstance(raw, list):
        raise ApiError(400, "items must be a list.")
    merged = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ApiError(400, "Each build item must be an object.")
        pid = number_field(item, "product_id", "Product", integer=True, lo=1)
        qty = number_field(item, "quantity", "Quantity", integer=True, lo=1) if item.get("quantity") else 1
        listing_id = item.get("listing_id")
        if pid in merged:
            merged[pid]["quantity"] += qty
        else:
            merged[pid] = {"product_id": pid, "quantity": qty, "listing_id": listing_id}
    return list(merged.values())


def insert_build_items(con, build_id, items):
    for item in items:
        con.execute("INSERT INTO build_items(build_id, product_id, quantity) VALUES (?, ?, ?)",
                    (build_id, item["product_id"], item["quantity"]))


@route("POST", "/api/builds/check")
def check_build(con, req):
    """Price a build and run it through the v_build_issues compatibility view.

    The parts are inserted into a temporary build inside a transaction that is always rolled back
    (the same technique catalog.evaluate_candidates uses), so nothing is saved."""
    items = clean_build_items(con, req.body.get("items", []))
    details = []
    for item in items:
        product = con.execute(
            "SELECT p.product_id, p.name, p.brand, c.name AS category, c.multi_allowed, "
            "bp.best_price, bp.store AS best_store, bp.listing_id AS best_listing_id, "
            "(SELECT COUNT(*) FROM listings l WHERE l.product_id = p.product_id) AS listing_count "
            "FROM products p JOIN categories c ON c.category_id = p.category_id "
            "LEFT JOIN v_best_price bp ON bp.product_id = p.product_id WHERE p.product_id = ?",
            (item["product_id"],)).fetchone()
        if product is None:
            details.append({"product_id": item["product_id"], "missing": True})
            continue
        offer = None
        if item["listing_id"]:
            offer = con.execute("SELECT l.listing_id, l.price, l.availability, s.name AS store "
                                "FROM listings l JOIN stores s ON s.store_id = l.store_id "
                                "WHERE l.listing_id = ? AND l.product_id = ?",
                                (item["listing_id"], item["product_id"])).fetchone()
        d = dict(product)
        d["quantity"] = item["quantity"]
        d["selected_offer"] = dict(offer) if offer else None
        details.append(d)

    valid = [i for i, d in zip(items, details) if not d.get("missing")]
    issues, wattage = [], None
    con.execute("BEGIN")
    try:
        owner = req.user["user_id"] if req.user else con.execute("SELECT MIN(user_id) FROM users").fetchone()[0]
        build_id = con.execute("INSERT INTO builds(user_id, name) VALUES (?, 'check')", (owner,)).lastrowid
        try:
            insert_build_items(con, build_id, valid)
        except sqlite3.IntegrityError as e:
            raise ApiError(400, friendly_integrity_error(e))
        issues = [dict(r) for r in con.execute(
            "SELECT severity, rule, message FROM v_build_issues WHERE build_id = ? ORDER BY severity, rule",
            (build_id,))]
        # Same estimate the PSU_POWER rule uses: CPU TDP + GPU TDP + 100 W for everything else.
        cpu_w, gpu_w = con.execute(
            "SELECT (SELECT SUM(c.tdp_w * bi.quantity) FROM build_items bi JOIN cpu c ON c.product_id = bi.product_id "
            "        WHERE bi.build_id = ?), "
            "       (SELECT SUM(g.tdp_w * bi.quantity) FROM build_items bi JOIN gpu g ON g.product_id = bi.product_id "
            "        WHERE bi.build_id = ?)", (build_id, build_id)).fetchone()
        if cpu_w or gpu_w:
            wattage = (cpu_w or 0) + (gpu_w or 0) + 100
    finally:
        con.execute("ROLLBACK")

    return {"items": details, "issues": issues, "estimated_wattage": wattage}


def own_build(con, req, build_id):
    row = con.execute("SELECT * FROM builds WHERE build_id = ?", (int(build_id),)).fetchone()
    if row is None or row["user_id"] != req.user["user_id"]:
        raise ApiError(404, "Build not found.")
    return row


@route("GET", "/api/builds", auth="user")
def my_builds(con, req):
    rows = con.execute(
        "SELECT b.build_id, b.name, b.created_at, t.total_price, t.parts_without_price, "
        "(SELECT COUNT(*) FROM build_items bi WHERE bi.build_id = b.build_id) AS part_count, "
        "(SELECT COUNT(*) FROM v_build_issues i WHERE i.build_id = b.build_id AND i.severity = 'ERROR') AS errors, "
        "(SELECT COUNT(*) FROM v_build_issues i WHERE i.build_id = b.build_id AND i.severity = 'WARNING') AS missing "
        "FROM builds b JOIN v_build_total t ON t.build_id = b.build_id "
        "WHERE b.user_id = ? ORDER BY b.build_id DESC", (req.user["user_id"],)).fetchall()
    return [dict(r) for r in rows]


@route("GET", r"/api/builds/(\d+)", auth="user")
def get_build(con, req, build_id):
    build = own_build(con, req, build_id)
    items = con.execute("SELECT bi.product_id, bi.quantity, c.name AS category FROM build_items bi "
                        "JOIN products p ON p.product_id = bi.product_id "
                        "JOIN categories c ON c.category_id = p.category_id "
                        "WHERE bi.build_id = ? ORDER BY c.category_id", (build["build_id"],)).fetchall()
    return {"build": dict(build), "items": [dict(i) for i in items]}


@route("POST", "/api/builds", auth="user")
def create_build(con, req):
    name = text_field(req.body, "name", "Build name", max_len=100)
    items = clean_build_items(con, req.body.get("items", []))
    with db.tx(con):
        build_id = con.execute("INSERT INTO builds(user_id, name) VALUES (?, ?)",
                               (req.user["user_id"], name)).lastrowid
        insert_build_items(con, build_id, items)
    return {"build_id": build_id, "name": name}


@route("PUT", r"/api/builds/(\d+)", auth="user")
def update_build(con, req, build_id):
    build = own_build(con, req, build_id)
    name = text_field(req.body, "name", "Build name", max_len=100)
    items = clean_build_items(con, req.body.get("items", []))
    with db.tx(con):
        con.execute("UPDATE builds SET name = ? WHERE build_id = ?", (name, build["build_id"]))
        con.execute("DELETE FROM build_items WHERE build_id = ?", (build["build_id"],))
        insert_build_items(con, build["build_id"], items)
    return {"build_id": build["build_id"], "name": name}


@route("DELETE", r"/api/builds/(\d+)", auth="user")
def delete_build(con, req, build_id):
    build = own_build(con, req, build_id)
    con.execute("DELETE FROM builds WHERE build_id = ?", (build["build_id"],))   # build_items cascade
    return {"ok": True}


# Admin: products
LOOKUP_TABLES = {"socket": "socket_id", "form_factor": "form_factor_id"}


@route("GET", "/api/admin/lookups", auth="admin")
def admin_lookups(con, req):
    fields = {cat: [{"column": col, "kind": kind,
                     "options": extra if kind == "choice" else None,
                     "lookup": extra if kind == "lookup" else None,
                     "label": col.replace("_id", "").replace("_", " ")}
                    for col, kind, extra in specs]
              for cat, specs in SPEC_FIELDS.items()}
    return {
        "categories": [dict(r) for r in con.execute("SELECT category_id, name FROM categories ORDER BY category_id")],
        "sockets": [dict(r) for r in con.execute("SELECT socket_id AS id, name FROM socket ORDER BY name")],
        "form_factors": [dict(r) for r in con.execute("SELECT form_factor_id AS id, name FROM form_factor "
                                                      "ORDER BY form_factor_id")],
        "stores": [dict(r) for r in con.execute("SELECT store_id, name FROM stores ORDER BY name")],
        "products": [dict(r) for r in con.execute(
            "SELECT p.product_id, p.name, c.name AS category FROM products p "
            "JOIN categories c ON c.category_id = p.category_id ORDER BY c.category_id, p.name")],
        "spec_fields": fields,
        "availability": AVAILABILITY,
    }


@route("GET", "/api/admin/products", auth="admin")
def admin_products(con, req):
    where, params = ["1"], []
    if req.arg("category"):
        where.append("c.name = ?")
        params.append(req.arg("category"))
    if req.arg("q"):
        where.append("(p.name LIKE ? OR p.brand LIKE ? OR p.model LIKE ?)")
        params.extend([f"%{req.arg('q')}%"] * 3)
    sql = ("SELECT p.product_id, p.name, p.brand, p.model, c.name AS category, "
           "(SELECT COUNT(*) FROM listings l WHERE l.product_id = p.product_id) AS listing_count, "
           "(SELECT COUNT(*) FROM build_items bi WHERE bi.product_id = p.product_id) AS build_count "
           "FROM products p JOIN categories c ON c.category_id = p.category_id "
           f"WHERE {' AND '.join(where)}")
    sortable = {"id": "p.product_id", "name": "p.name", "category": "c.category_id", "brand": "p.brand",
                "listings": "listing_count"}
    return paginate(con, f"{sql} ORDER BY {sort_clause(req, sortable, 'id')}", params, req)


@route("GET", r"/api/admin/products/(\d+)", auth="admin")
def admin_product(con, req, product_id):
    product = product_or_404(con, int(product_id))
    category = product["category"]
    spec = con.execute(f"SELECT * FROM {SPEC_TABLE[category]} WHERE product_id = ?",
                       (product["product_id"],)).fetchone() if category in SPEC_TABLE else None
    links = []
    if category == "Case":
        links = [r[0] for r in con.execute("SELECT form_factor_id FROM case_form_factor WHERE product_id = ?",
                                           (product["product_id"],))]
    elif category == "Cooler":
        links = [r[0] for r in con.execute("SELECT socket_id FROM cooler_socket WHERE product_id = ?",
                                           (product["product_id"],))]
    return {"product": dict(product), "spec": dict(spec) if spec else {}, "links": links}


def read_product_form(con, body, category):
    """Validate the product form. Returns (brand, model, summary, spec values, link ids)."""
    brand = text_field(body, "brand", "Brand", max_len=100)
    model = text_field(body, "model", "Model", max_len=100)
    summary = text_field(body, "specification", "Specification text", required=False, max_len=1000)
    spec_in = body.get("spec") or {}
    specs = {}
    for col, kind, extra in SPEC_FIELDS.get(category, []):
        label = col.replace("_id", "").replace("_", " ").capitalize()
        if kind == "int":
            specs[col] = number_field(spec_in, col, label, integer=True, lo=0)
        elif kind == "float":
            specs[col] = number_field(spec_in, col, label, lo=0)
        elif kind == "text":
            specs[col] = text_field(spec_in, col, label, max_len=50)
        elif kind == "choice":
            if spec_in.get(col) not in extra:
                raise ApiError(400, f"{label} must be one of: {', '.join(extra)}.")
            specs[col] = spec_in[col]
        else:
            value = number_field(spec_in, col, label, integer=True)
            if con.execute(f"SELECT 1 FROM {extra} WHERE {LOOKUP_TABLES[extra]} = ?", (value,)).fetchone() is None:
                raise ApiError(400, f"Please choose a valid {label.lower()}.")
            specs[col] = value

    links = []
    if category in ("Case", "Cooler"):
        table = "form_factor" if category == "Case" else "socket"
        try:
            links = sorted({int(v) for v in body.get("links") or []})
        except (TypeError, ValueError):
            raise ApiError(400, "Invalid selection.")
        if not links:
            raise ApiError(400, "Select at least one supported motherboard size." if category == "Case"
                           else "Select at least one supported CPU socket.")
        valid = {r[0] for r in con.execute(f"SELECT {LOOKUP_TABLES[table]} FROM {table}")}
        if not set(links) <= valid:
            raise ApiError(400, "Invalid selection.")
    return brand, model, summary, specs, links


def write_links(con, category, product_id, links):
    link_table = {"Case": ("case_form_factor", "form_factor_id"), "Cooler": ("cooler_socket", "socket_id")}
    if category not in link_table:
        return
    table, column = link_table[category]
    con.execute(f"DELETE FROM {table} WHERE product_id = ?", (product_id,))
    for value in links:
        con.execute(f"INSERT INTO {table}(product_id, {column}) VALUES (?, ?)", (product_id, value))


@route("POST", "/api/admin/products", auth="admin")
def admin_create_product(con, req):
    category = get_category(con, text_field(req.body, "category", "Category"))
    brand, model, summary, specs, links = read_product_form(con, req.body, category["name"])
    with db.tx(con):
        pid = con.execute("INSERT INTO products(category_id, name, brand, model, specification) VALUES (?,?,?,?,?)",
                          (category["category_id"], f"{brand} {model}", brand, model, summary)).lastrowid
        if category["name"] in SPEC_TABLE:
            cols = ["product_id"] + list(specs)
            con.execute(f"INSERT INTO {SPEC_TABLE[category['name']]}({', '.join(cols)}) "
                        f"VALUES ({', '.join('?' * len(cols))})", [pid] + list(specs.values()))
        write_links(con, category["name"], pid, links)
    return {"product_id": pid, "name": f"{brand} {model}"}


@route("PUT", r"/api/admin/products/(\d+)", auth="admin")
def admin_update_product(con, req, product_id):
    product = product_or_404(con, int(product_id))
    category = product["category"]
    brand, model, summary, specs, links = read_product_form(con, req.body, category)
    with db.tx(con):
        con.execute("UPDATE products SET brand = ?, model = ?, name = ?, specification = ? WHERE product_id = ?",
                    (brand, model, f"{brand} {model}", summary, product["product_id"]))
        if category in SPEC_TABLE and specs:
            assignments = ", ".join(f"{col} = ?" for col in specs)
            updated = con.execute(f"UPDATE {SPEC_TABLE[category]} SET {assignments} WHERE product_id = ?",
                                  list(specs.values()) + [product["product_id"]]).rowcount
            if not updated:
                cols = ["product_id"] + list(specs)
                con.execute(f"INSERT INTO {SPEC_TABLE[category]}({', '.join(cols)}) "
                            f"VALUES ({', '.join('?' * len(cols))})", [product["product_id"]] + list(specs.values()))
        write_links(con, category, product["product_id"], links)
    return {"product_id": product["product_id"], "name": f"{brand} {model}"}


@route("DELETE", r"/api/admin/products/(\d+)", auth="admin")
def admin_delete_product(con, req, product_id):
    product = product_or_404(con, int(product_id))
    try:
        con.execute("DELETE FROM products WHERE product_id = ?", (product["product_id"],))
    except sqlite3.IntegrityError:
        raise ApiError(409, "This product still has store listings or appears in saved builds. "
                            "Delete those first, then try again.")
    return {"ok": True}


# Admin: listings
@route("GET", "/api/admin/listings", auth="admin")
def admin_listings(con, req):
    where, params = ["1"], []
    for arg, column in (("product_id", "l.product_id"), ("store_id", "l.store_id")):
        value = req.arg_int(arg)
        if value is not None:
            where.append(f"{column} = ?")
            params.append(value)
    if req.arg("availability") in AVAILABILITY:
        where.append("l.availability = ?")
        params.append(req.arg("availability"))
    if req.arg("q"):
        where.append("p.name LIKE ?")
        params.append(f"%{req.arg('q')}%")
    stale_days = req.arg_int("stale_days", None, 0)
    if stale_days is not None:
        where.append("julianday('now') - julianday(l.last_updated) >= ?")
        params.append(stale_days)
    sql = ("SELECT l.listing_id, l.product_id, p.name AS product, l.store_id, s.name AS store, l.price, "
           "l.availability, l.product_url, l.last_updated, u.username AS created_by "
           "FROM listings l JOIN products p ON p.product_id = l.product_id "
           "JOIN stores s ON s.store_id = l.store_id JOIN users u ON u.user_id = l.created_by_user_id "
           f"WHERE {' AND '.join(where)}")
    sortable = {"id": "l.listing_id", "product": "p.name", "store": "s.name", "price": "l.price",
                "availability": "l.availability", "updated": "l.last_updated"}
    return paginate(con, f"{sql} ORDER BY {sort_clause(req, sortable, 'product')}, s.name", params, req)


def read_listing_form(body):
    price = number_field(body, "price", "Price", lo=0)
    if round(price, 2) != price:
        raise ApiError(400, "Price can have at most two decimal places.")
    availability = body.get("availability")
    if availability not in AVAILABILITY:
        raise ApiError(400, "Choose a valid availability.")
    url = text_field(body, "product_url", "Product URL", required=False, max_len=500)
    if url and not re.match(r"^https?://", url):
        raise ApiError(400, "Product URL must start with http:// or https://")
    return price, availability, url


@route("POST", "/api/admin/listings", auth="admin")
def admin_create_listing(con, req):
    product_id = number_field(req.body, "product_id", "Product", integer=True)
    store_id = number_field(req.body, "store_id", "Store", integer=True)
    price, availability, url = read_listing_form(req.body)
    if con.execute("SELECT 1 FROM products WHERE product_id = ?", (product_id,)).fetchone() is None:
        raise ApiError(400, "Please choose an existing product.")
    if con.execute("SELECT 1 FROM stores WHERE store_id = ?", (store_id,)).fetchone() is None:
        raise ApiError(400, "Please choose an existing store.")
    listing_id = con.execute(
        "INSERT INTO listings(product_id, store_id, created_by_user_id, price, availability, product_url, "
        "last_updated) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (product_id, store_id, req.user["user_id"], price, availability, url)).lastrowid
    return {"listing_id": listing_id}


@route("PUT", r"/api/admin/listings/(\d+)", auth="admin")
def admin_update_listing(con, req, listing_id):
    price, availability, url = read_listing_form(req.body)
    n = con.execute("UPDATE listings SET price = ?, availability = ?, product_url = ? WHERE listing_id = ?",
                    (price, availability, url, int(listing_id))).rowcount   # trigger refreshes last_updated
    if not n:
        raise ApiError(404, "Listing not found.")
    return {"listing_id": int(listing_id)}


@route("DELETE", r"/api/admin/listings/(\d+)", auth="admin")
def admin_delete_listing(con, req, listing_id):
    if not con.execute("DELETE FROM listings WHERE listing_id = ?", (int(listing_id),)).rowcount:
        raise ApiError(404, "Listing not found.")
    return {"ok": True}


# Admin: stores and users
def read_store_form(body):
    name = text_field(body, "name", "Store name", max_len=100)
    website = text_field(body, "website", "Website", required=False)
    if website and not re.match(r"^https?://", website):
        raise ApiError(400, "Website must start with http:// or https://")
    return name, website


@route("POST", "/api/admin/stores", auth="admin")
def admin_create_store(con, req):
    name, website = read_store_form(req.body)
    return {"store_id": con.execute("INSERT INTO stores(name, website) VALUES (?, ?)", (name, website)).lastrowid}


@route("PUT", r"/api/admin/stores/(\d+)", auth="admin")
def admin_update_store(con, req, store_id):
    name, website = read_store_form(req.body)
    if not con.execute("UPDATE stores SET name = ?, website = ? WHERE store_id = ?",
                       (name, website, int(store_id))).rowcount:
        raise ApiError(404, "Store not found.")
    return {"store_id": int(store_id)}


@route("DELETE", r"/api/admin/stores/(\d+)", auth="admin")
def admin_delete_store(con, req, store_id):
    try:
        n = con.execute("DELETE FROM stores WHERE store_id = ?", (int(store_id),)).rowcount
    except sqlite3.IntegrityError:
        raise ApiError(409, "This store still has listings. Delete those listings first.")
    if not n:
        raise ApiError(404, "Store not found.")
    return {"ok": True}


@route("GET", "/api/admin/users", auth="admin")
def admin_users(con, req):
    q = f"%{req.arg('q', '')}%"
    sql = ("SELECT u.user_id, u.username, u.email, u.role, "
           "(SELECT COUNT(*) FROM builds b WHERE b.user_id = u.user_id) AS build_count, "
           "(SELECT COUNT(*) FROM listings l WHERE l.created_by_user_id = u.user_id) AS listing_count "
           "FROM users u WHERE u.username LIKE ? OR u.email LIKE ?")
    return paginate(con, f"{sql} ORDER BY u.user_id", [q, q], req)


@route("POST", "/api/admin/users", auth="admin")
def admin_create_user(con, req):
    username = text_field(req.body, "username", "Username", max_len=50)
    email = text_field(req.body, "email", "E-mail")
    role = req.body.get("role", "customer")
    if "@" not in email:
        raise ApiError(400, "Please enter a valid e-mail address.")
    if role not in ("customer", "admin"):
        raise ApiError(400, "Role must be customer or admin.")
    uid = con.execute("INSERT INTO users(username, email, role) VALUES (?, ?, ?)", (username, email, role)).lastrowid
    return {"user_id": uid}


@route("PUT", r"/api/admin/users/(\d+)", auth="admin")
def admin_update_user(con, req, user_id):
    if int(user_id) == req.user["user_id"]:
        raise ApiError(400, "You cannot change your own role.")
    role = req.body.get("role")
    if role not in ("customer", "admin"):
        raise ApiError(400, "Role must be customer or admin.")
    if not con.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, int(user_id))).rowcount:
        raise ApiError(404, "User not found.")
    return {"user_id": int(user_id)}


@route("DELETE", r"/api/admin/users/(\d+)", auth="admin")
def admin_delete_user(con, req, user_id):
    if int(user_id) == req.user["user_id"]:
        raise ApiError(400, "You cannot delete your own account.")
    try:
        n = con.execute("DELETE FROM users WHERE user_id = ?", (int(user_id),)).rowcount
    except sqlite3.IntegrityError:
        raise ApiError(409, "This administrator created listings and cannot be deleted.")
    if not n:
        raise ApiError(404, "User not found.")
    for token, uid in list(SESSIONS.items()):
        if uid == int(user_id):
            SESSIONS.pop(token, None)
    return {"ok": True}


# HTTP server
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self, method):
        url = urlsplit(self.path)
        if not url.path.startswith("/api/"):
            if method == "GET":
                return self.serve_frontend(url.path)
            return self.send_json(405, {"error": "Method not allowed."})

        handler, args = None, ()
        for m, pattern, auth, fn in ROUTES:
            match = pattern.match(url.path)
            if match and m == method:
                handler, args = (auth, fn), match.groups()
                break
        if handler is None:
            return self.send_json(404, {"error": "Not found."})

        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self.send_json(400, {"error": "Request body must be a JSON object."})

        con = db.connect()
        try:
            auth, fn = handler
            user = current_user(con, self.headers)
            if auth and user is None:
                raise ApiError(401, "Please log in first.")
            if auth == "admin" and user["role"] != "admin":
                raise ApiError(403, "This action requires an administrator account.")
            self.send_json(200, fn(con, Request(parse_qs(url.query), body, user), *args))
        except ApiError as e:
            self.send_json(e.status, {"error": e.message})
        except sqlite3.IntegrityError as e:
            self.send_json(409, {"error": friendly_integrity_error(e)})
        except sqlite3.Error as e:
            self.send_json(500, {"error": f"Database error: {e}"})
        finally:
            con.close()

    def serve_frontend(self, path):
        if not os.path.isdir(DIST_DIR):
            return self.send_json(404, {"error": "Frontend not built. Run `npm run build` in frontend/, "
                                                 "or use `npm run dev` during development."})
        file_path = os.path.realpath(os.path.join(DIST_DIR, path.lstrip("/")))
        if os.path.commonpath((DIST_DIR, file_path)) != DIST_DIR or not os.path.isfile(file_path):
            file_path = os.path.join(DIST_DIR, "index.html")   # client-side route
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file_path)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}\n")


def main():
    if not os.path.exists(db.DB_PATH):
        sys.exit(f"Database not found at {db.DB_PATH}\nCreate it with: python3 backend/generate_data.py")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"API running at http://localhost:{PORT}/api  (database: {db.DB_PATH})")
    if os.path.isdir(DIST_DIR):
        print(f"Website: http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
