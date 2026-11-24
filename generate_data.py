#!/usr/bin/env python3
"""
Rebuilds pcparts.db: runs schema.sql and then fills the tables with sample data.
Run with: python generate_data.py

Product names are real but specs and prices are approximate. Stores, users,
prices and builds are random (fixed seed, so it gives the same data every time).
"""
import datetime as dt
import os
import random
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "pcparts.db")
SCHEMA_PATH = os.path.join(HERE, "schema.sql")
SEED = 42
N_CUSTOMERS = 40
N_BUILDS = 120
TODAY = dt.date(2026, 11, 15)

rng = random.Random(SEED)

# product catalog
SOCKETS = ["AM4", "AM5", "LGA1200", "LGA1700", "LGA1851"]
FORM_FACTORS = ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"]

# name, required, multi_allowed
CATEGORIES = [
    ("CPU", 1, 0), ("Motherboard", 1, 0), ("RAM", 1, 1), ("GPU", 0, 0),
    ("Storage", 1, 1), ("PSU", 1, 0), ("Case", 1, 0), ("Cooler", 0, 0),
]


# brand, name, socket, cores, threads, base, boost, tdp, price
CPUS = [
    ("AMD", "Ryzen 5 5600", "AM4", 6, 12, 3.5, 4.4, 65, 129),
    ("AMD", "Ryzen 7 5800X3D", "AM4", 8, 16, 3.4, 4.5, 105, 299),
    ("AMD", "Ryzen 5 7600", "AM5", 6, 12, 3.8, 5.1, 65, 199),
    ("AMD", "Ryzen 5 7600X", "AM5", 6, 12, 4.7, 5.3, 105, 229),
    ("AMD", "Ryzen 7 7700X", "AM5", 8, 16, 4.5, 5.4, 105, 299),
    ("AMD", "Ryzen 7 7800X3D", "AM5", 8, 16, 4.2, 5.0, 120, 399),
    ("AMD", "Ryzen 9 7900X", "AM5", 12, 24, 4.7, 5.6, 170, 399),
    ("AMD", "Ryzen 9 7950X", "AM5", 16, 32, 4.5, 5.7, 170, 549),
    ("AMD", "Ryzen 5 9600X", "AM5", 6, 12, 3.9, 5.4, 65, 279),
    ("AMD", "Ryzen 7 9800X3D", "AM5", 8, 16, 4.7, 5.2, 120, 479),
    ("AMD", "Ryzen 9 9950X", "AM5", 16, 32, 4.3, 5.7, 170, 599),
    ("Intel", "Core i5-10400F", "LGA1200", 6, 12, 2.9, 4.3, 65, 119),
    ("Intel", "Core i7-11700K", "LGA1200", 8, 16, 3.6, 5.0, 125, 249),
    ("Intel", "Core i3-12100F", "LGA1700", 4, 8, 3.3, 4.3, 58, 99),
    ("Intel", "Core i5-12400F", "LGA1700", 6, 12, 2.5, 4.4, 65, 149),
    ("Intel", "Core i5-13400F", "LGA1700", 10, 16, 2.5, 4.6, 65, 189),
    ("Intel", "Core i5-13600K", "LGA1700", 14, 20, 3.5, 5.1, 125, 279),
    ("Intel", "Core i7-13700K", "LGA1700", 16, 24, 3.4, 5.4, 125, 349),
    ("Intel", "Core i7-14700K", "LGA1700", 20, 28, 3.4, 5.6, 125, 399),
    ("Intel", "Core i9-14900K", "LGA1700", 24, 32, 3.2, 6.0, 125, 549),
    ("Intel", "Core Ultra 5 245K", "LGA1851", 14, 14, 4.2, 5.2, 125, 309),
    ("Intel", "Core Ultra 7 265K", "LGA1851", 20, 20, 3.9, 5.5, 125, 394),
    ("Intel", "Core Ultra 9 285K", "LGA1851", 24, 24, 3.7, 5.7, 125, 589),
]

# brand, name, chipset, socket, form factor, ram, slots, max_gb, m2, sata, price
MOTHERBOARDS = [
    ("ASUS", "PRIME B450M-A II", "B450", "AM4", "Micro-ATX", "DDR4", 4, 64, 1, 4, 89),
    ("MSI", "B550 GAMING PLUS", "B550", "AM4", "ATX", "DDR4", 4, 128, 2, 6, 119),
    ("Gigabyte", "B550M DS3H", "B550", "AM4", "Micro-ATX", "DDR4", 4, 128, 1, 4, 99),
    ("ASUS", "ROG STRIX X570-E GAMING", "X570", "AM4", "ATX", "DDR4", 4, 128, 3, 8, 279),
    ("ASRock", "B550 Phantom Gaming-ITX/ax", "B550", "AM4", "Mini-ITX", "DDR4", 2, 64, 2, 4, 169),
    ("MSI", "PRO B650-P WIFI", "B650", "AM5", "ATX", "DDR5", 4, 192, 2, 4, 159),
    ("Gigabyte", "B650M AORUS ELITE AX", "B650", "AM5", "Micro-ATX", "DDR5", 4, 192, 2, 4, 179),
    ("ASUS", "TUF GAMING B650-PLUS WIFI", "B650", "AM5", "ATX", "DDR5", 4, 192, 3, 4, 189),
    ("ASRock", "B650E PG-ITX WIFI", "B650E", "AM5", "Mini-ITX", "DDR5", 2, 96, 2, 2, 239),
    ("ASUS", "ROG STRIX X670E-E GAMING WIFI", "X670E", "AM5", "ATX", "DDR5", 4, 192, 4, 6, 449),
    ("MSI", "MEG X670E ACE", "X670E", "AM5", "E-ATX", "DDR5", 4, 192, 5, 6, 699),
    ("Gigabyte", "X870E AORUS PRO", "X870E", "AM5", "ATX", "DDR5", 4, 256, 4, 4, 369),
    ("ASRock", "B460M Pro4", "B460", "LGA1200", "Micro-ATX", "DDR4", 4, 128, 1, 6, 79),
    ("MSI", "MAG Z590 TOMAHAWK WIFI", "Z590", "LGA1200", "ATX", "DDR4", 4, 128, 3, 6, 189),
    ("MSI", "PRO B660M-A DDR4", "B660", "LGA1700", "Micro-ATX", "DDR4", 4, 128, 2, 4, 109),
    ("Gigabyte", "B760 GAMING X DDR4", "B760", "LGA1700", "ATX", "DDR4", 4, 128, 3, 4, 139),
    ("ASUS", "PRIME B760M-A WIFI", "B760", "LGA1700", "Micro-ATX", "DDR5", 4, 192, 2, 4, 149),
    ("MSI", "MAG B760 TOMAHAWK WIFI", "B760", "LGA1700", "ATX", "DDR5", 4, 192, 3, 4, 189),
    ("ASRock", "B760I Lightning WiFi", "B760", "LGA1700", "Mini-ITX", "DDR5", 2, 96, 2, 4, 199),
    ("Gigabyte", "Z790 AORUS ELITE AX", "Z790", "LGA1700", "ATX", "DDR5", 4, 192, 4, 6, 259),
    ("MSI", "MPG Z790 CARBON WIFI", "Z790", "LGA1700", "ATX", "DDR5", 4, 192, 5, 6, 379),
    ("ASUS", "ROG STRIX Z790-E GAMING WIFI", "Z790", "LGA1700", "ATX", "DDR5", 4, 192, 5, 6, 449),
    ("ASUS", "ROG MAXIMUS Z790 EXTREME", "Z790", "LGA1700", "E-ATX", "DDR5", 4, 192, 5, 8, 899),
    ("ASUS", "PRIME Z890-P WIFI", "Z890", "LGA1851", "ATX", "DDR5", 4, 192, 3, 4, 279),
    ("MSI", "MAG B860 TOMAHAWK WIFI", "B860", "LGA1851", "ATX", "DDR5", 4, 192, 3, 4, 229),
    ("Gigabyte", "B860M AORUS ELITE WIFI", "B860", "LGA1851", "Micro-ATX", "DDR5", 4, 192, 2, 4, 199),
    ("ASRock", "Z890I NOVA WIFI", "Z890", "LGA1851", "Mini-ITX", "DDR5", 2, 96, 2, 2, 349),
]

# brand, name, type, total GB, modules, MHz, price
RAMS = [
    ("Crucial", "Basics 8GB (1x8GB) DDR4-2666", "DDR4", 8, 1, 2666, 24),
    ("Corsair", "Vengeance LPX 16GB (2x8GB) DDR4-3200", "DDR4", 16, 2, 3200, 45),
    ("Corsair", "Vengeance LPX 32GB (2x16GB) DDR4-3200", "DDR4", 32, 2, 3200, 79),
    ("G.Skill", "Ripjaws V 16GB (2x8GB) DDR4-3600", "DDR4", 16, 2, 3600, 49),
    ("G.Skill", "Ripjaws V 32GB (2x16GB) DDR4-3600", "DDR4", 32, 2, 3600, 85),
    ("Kingston", "FURY Beast 64GB (2x32GB) DDR4-3200", "DDR4", 64, 2, 3200, 159),
    ("Corsair", "Vengeance 128GB (4x32GB) DDR4-3200", "DDR4", 128, 4, 3200, 299),
    ("Crucial", "Pro 16GB (1x16GB) DDR5-4800", "DDR5", 16, 1, 4800, 49),
    ("Corsair", "Vengeance 16GB (2x8GB) DDR5-5600", "DDR5", 16, 2, 5600, 65),
    ("Kingston", "FURY Beast 32GB (2x16GB) DDR5-5200", "DDR5", 32, 2, 5200, 99),
    ("Corsair", "Vengeance 32GB (2x16GB) DDR5-6000", "DDR5", 32, 2, 6000, 109),
    ("G.Skill", "Trident Z5 RGB 32GB (2x16GB) DDR5-6400", "DDR5", 32, 2, 6400, 139),
    ("Kingston", "FURY Renegade 48GB (2x24GB) DDR5-7200", "DDR5", 48, 2, 7200, 189),
    ("G.Skill", "Trident Z5 64GB (2x32GB) DDR5-6000", "DDR5", 64, 2, 6000, 219),
    ("TeamGroup", "T-Create Expert 96GB (2x48GB) DDR5-6000", "DDR5", 96, 2, 6000, 309),
    ("Corsair", "Dominator Titanium 64GB (2x32GB) DDR5-6600", "DDR5", 64, 2, 6600, 329),
    ("G.Skill", "Trident Z5 128GB (4x32GB) DDR5-5600", "DDR5", 128, 4, 5600, 489),
]

# brand, name, chipset, vram, length, tdp, min psu, price
GPUS = [
    ("Intel", "Arc B580 Limited Edition 12GB", "Arc B580", 12, 272, 190, 600, 249),
    ("MSI", "GeForce RTX 3050 VENTUS 2X 8GB", "RTX 3050", 8, 235, 130, 550, 219),
    ("Sapphire", "PULSE Radeon RX 7600 8GB", "RX 7600", 8, 240, 165, 550, 269),
    ("Sapphire", "PULSE Radeon RX 9060 XT 16GB", "RX 9060 XT", 16, 240, 160, 550, 349),
    ("ASUS", "DUAL GeForce RTX 4060 8GB", "RTX 4060", 8, 227, 115, 550, 299),
    ("Gigabyte", "GeForce RTX 4060 Ti EAGLE 8GB", "RTX 4060 Ti", 8, 272, 160, 550, 399),
    ("XFX", "Speedster Radeon RX 7700 XT 12GB", "RX 7700 XT", 12, 322, 245, 700, 449),
    ("MSI", "GeForce RTX 5070 VENTUS 3X 12GB", "RTX 5070", 12, 303, 250, 650, 549),
    ("Sapphire", "NITRO+ Radeon RX 7800 XT 16GB", "RX 7800 XT", 16, 320, 263, 700, 529),
    ("MSI", "GeForce RTX 4070 SUPER VENTUS 2X 12GB", "RTX 4070 SUPER", 12, 242, 220, 650, 599),
    ("PowerColor", "Hellhound Radeon RX 9070 XT 16GB", "RX 9070 XT", 16, 330, 304, 750, 649),
    ("MSI", "GeForce RTX 5070 Ti GAMING TRIO 16GB", "RTX 5070 Ti", 16, 338, 300, 750, 749),
    ("ASUS", "TUF GeForce RTX 4070 Ti SUPER 16GB", "RTX 4070 Ti SUPER", 16, 348, 285, 700, 849),
    ("ASUS", "TUF Radeon RX 7900 XTX 24GB", "RX 7900 XTX", 24, 355, 355, 800, 949),
    ("Gigabyte", "GeForce RTX 4080 SUPER GAMING OC 16GB", "RTX 4080 SUPER", 16, 340, 320, 750, 999),
    ("MSI", "GeForce RTX 5080 SUPRIM 16GB", "RTX 5080", 16, 357, 360, 850, 1199),
    ("MSI", "GeForce RTX 4090 GAMING X TRIO 24GB", "RTX 4090", 24, 337, 450, 850, 1799),
    ("ASUS", "ROG STRIX GeForce RTX 5090 32GB", "RTX 5090", 32, 357, 575, 1000, 1999),
]

# brand, name, watts, efficiency, modular, price
PSUS = [
    ("Cooler Master", "MWE 400 Bronze V2 400W", 400, "80+ Bronze", "No", 39),
    ("Corsair", "CV450 450W", 450, "80+ Bronze", "No", 49),
    ("Corsair", "CX550 550W", 550, "80+ Bronze", "No", 59),
    ("Seasonic", "Focus GX-550 550W", 550, "80+ Gold", "Full", 99),
    ("EVGA", "600 W1 600W", 600, "80+ White", "No", 55),
    ("Corsair", "RM650e 650W", 650, "80+ Gold", "Full", 99),
    ("Seasonic", "Focus GX-750 750W", 750, "80+ Gold", "Full", 129),
    ("Corsair", "SF750 SFX 750W", 750, "80+ Platinum", "Full", 169),
    ("MSI", "MAG A850GL 850W", 850, "80+ Gold", "Full", 119),
    ("Corsair", "RM850x 850W", 850, "80+ Gold", "Full", 149),
    ("be quiet!", "Straight Power 11 1000W", 1000, "80+ Platinum", "Full", 199),
    ("Corsair", "HX1000i 1000W", 1000, "80+ Platinum", "Full", 239),
    ("Corsair", "HX1200i 1200W", 1200, "80+ Platinum", "Full", 279),
    ("ASUS", "ROG THOR 1600W Titanium", 1600, "80+ Titanium", "Full", 549),
]

ALL = ["ATX", "Micro-ATX", "Mini-ITX"]
# brand, name, max gpu mm, max cooler mm, form factors, price
CASES = [
    ("Cooler Master", "MasterBox Q300L", 360, 159, ["Micro-ATX", "Mini-ITX"], 49),
    ("Thermaltake", "Core V1 Mini-ITX", 285, 140, ["Mini-ITX"], 59),
    ("Cooler Master", "NR200P Mini-ITX", 330, 155, ["Mini-ITX"], 99),
    ("Fractal Design", "Terra Mini-ITX", 322, 77, ["Mini-ITX"], 179),
    ("Montech", "AIR 903 MAX", 400, 170, ALL, 89),
    ("be quiet!", "Pure Base 500", 369, 190, ALL, 89),
    ("NZXT", "H5 Flow", 365, 165, ALL, 94),
    ("Phanteks", "Eclipse G360A", 400, 162, ALL, 99),
    ("Lian Li", "LANCOOL 216", 392, 180, ["E-ATX"] + ALL, 99),
    ("Corsair", "4000D Airflow", 360, 170, ALL, 104),
    ("Fractal Design", "North", 355, 170, ALL, 139),
    ("Lian Li", "O11 Dynamic EVO", 426, 167, ["E-ATX"] + ALL, 169),
    ("Corsair", "7000D Airflow", 450, 190, ["E-ATX"] + ALL, 239),
]

# brand, name, type, capacity GB, price
STORAGE = [
    ("Kingston", "NV2 500GB NVMe", "NVMe SSD", 500, 35),
    ("WD", "Blue SN580 500GB NVMe", "NVMe SSD", 500, 49),
    ("Crucial", "P3 Plus 1TB NVMe", "NVMe SSD", 1000, 59),
    ("WD", "Black SN850X 1TB NVMe", "NVMe SSD", 1000, 89),
    ("Samsung", "990 PRO 1TB NVMe", "NVMe SSD", 1000, 109),
    ("Kingston", "NV3 2TB NVMe", "NVMe SSD", 2000, 99),
    ("Samsung", "990 PRO 2TB NVMe", "NVMe SSD", 2000, 179),
    ("Crucial", "T700 2TB NVMe Gen5", "NVMe SSD", 2000, 259),
    ("Seagate", "FireCuda 530 4TB NVMe", "NVMe SSD", 4000, 349),
    ("WD", "Blue SA510 500GB SATA SSD", "SATA SSD", 500, 45),
    ("Crucial", "MX500 1TB SATA SSD", "SATA SSD", 1000, 79),
    ("Samsung", "870 EVO 2TB SATA SSD", "SATA SSD", 2000, 149),
    ("Samsung", "870 QVO 4TB SATA SSD", "SATA SSD", 4000, 279),
    ("Seagate", "Barracuda 1TB HDD", "HDD", 1000, 44),
    ("Seagate", "Barracuda 2TB HDD", "HDD", 2000, 54),
    ("Toshiba", "P300 3TB HDD", "HDD", 3000, 74),
    ("WD", "Blue 4TB HDD", "HDD", 4000, 89),
    ("WD", "Red Plus 6TB HDD", "HDD", 6000, 139),
    ("Seagate", "IronWolf 8TB HDD", "HDD", 8000, 169),
]

ALLS = ["AM4", "AM5", "LGA1200", "LGA1700", "LGA1851"]
INTEL = ["LGA1200", "LGA1700", "LGA1851"]
# brand, name, type, height mm, max tdp W, sockets, price
COOLERS = [
    ("Noctua", "NH-L9i low-profile", "Air", 37, 65, INTEL, 49),
    ("Noctua", "NH-L9a-AM5 low-profile", "Air", 37, 65, ["AM4", "AM5"], 49),
    ("Thermalright", "AXP90-X53 low-profile", "Air", 53, 100, ALLS, 29),
    ("DeepCool", "AK400", "Air", 155, 220, ALLS, 32),
    ("Cooler Master", "Hyper 212 Black", "Air", 158, 150, ["AM4", "AM5", "LGA1200", "LGA1700"], 35),
    ("Thermalright", "Peerless Assassin 120 SE", "Air", 155, 250, ALLS, 39),
    ("Noctua", "NH-U12S", "Air", 158, 200, ALLS, 74),
    ("DeepCool", "AK620", "Air", 160, 260, ALLS, 65),
    ("Noctua", "NH-D15", "Air", 165, 250, ALLS, 109),
    ("be quiet!", "Dark Rock Pro 5", "Air", 168, 270, ALLS, 99),
    ("Arctic", "Liquid Freezer III 240", "Liquid", 55, 300, ALLS, 89),
    ("NZXT", "Kraken 280", "Liquid", 55, 300, ALLS, 149),
    ("Corsair", "iCUE H150i Elite 360", "Liquid", 55, 350, ALLS, 199),
]



FIRST = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth",
         "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Daniel", "Karen",
         "Matthew", "Nancy", "Anthony", "Lisa", "Mark", "Betty", "Steven", "Sandra", "Andrew", "Ashley",
         "Kevin", "Emily", "Brian", "Priya", "Wei", "Carlos", "Fatima", "Yuki", "Olga", "Mateo"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
        "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Patel", "Kim"]
BUILD_NAMES = ["Budget Gamer", "4K Beast", "Video Editing Rig", "Mini-ITX Living Room PC", "Streaming Setup",
               "Office Workhorse", "Esports Build", "First PC", "Silent Workstation", "Dream Build", "Upgrade Plan"]


STORES = [
    ("Newegg", "https://www.newegg.example"), ("Amazon", "https://www.amazon.example"),
    ("Micro Center", "https://www.microcenter.example"), ("B&H Photo Video", "https://www.bhphoto.example"),
    ("Best Buy", "https://www.bestbuy.example"), ("Central Computer", "https://www.centralcomputer.example"),
    ("Adorama", "https://www.adorama.example"), ("Memory Express", "https://www.memoryexpress.example"),
]
ADMINS = [("dwhitfield", "dana.whitfield@pcparts.example"), ("mortega", "marcus.ortega@pcparts.example"),
          ("lfischer", "lena.fischer@pcparts.example")]
CAT_DESC = {"CPU": "Processors", "Motherboard": "Motherboards", "RAM": "Memory kits", "GPU": "Graphics cards",
            "Storage": "SSDs and hard drives", "PSU": "Power supplies", "Case": "PC cases", "Cooler": "CPU coolers"}


def slug(s):
    return "".join(ch if ch.isalnum() else "-" for ch in s.lower()).strip("-")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        con.executescript(f.read())
    cur = con.cursor()

    # lookups
    sock = {s: cur.execute("INSERT INTO socket(name) VALUES (?)", (s,)).lastrowid for s in SOCKETS}
    ff = {s: cur.execute("INSERT INTO form_factor(name) VALUES (?)", (s,)).lastrowid for s in FORM_FACTORS}
    cat = {}
    for name, req, multi in CATEGORIES:
        cat[name] = cur.execute("INSERT INTO categories(name, description, required, multi_allowed) VALUES (?,?,?,?)",
                                (name, CAT_DESC[name], req, multi)).lastrowid

    base_price = {}

    def add_product(category, brand, model, spec, price):
        pid = cur.execute("INSERT INTO products(category_id, name, brand, model, specification) VALUES (?,?,?,?,?)",
                          (cat[category], f"{brand} {model}", brand, model, spec)).lastrowid
        base_price[pid] = price
        return pid

    # catalog (core row in products + specification row)
    for b, n, s, c, t, bg, bo, tdp, pr in CPUS:
        pid = add_product("CPU", b, n, f"Socket {s}, {c} cores / {t} threads, {bg}-{bo} GHz, {tdp} W TDP", pr)
        cur.execute("INSERT INTO cpu VALUES (?,?,?,?,?,?,?)", (pid, sock[s], c, t, bg, bo, tdp))
    for b, n, chip, s, f, rt, sl, mx, m2, sata, pr in MOTHERBOARDS:
        pid = add_product("Motherboard", b, n, f"{chip} chipset, socket {s}, {f}, {rt}, {sl} RAM slots "
                          f"(max {mx} GB), {m2} M.2, {sata} SATA", pr)
        cur.execute("INSERT INTO motherboard VALUES (?,?,?,?,?,?,?,?,?)", (pid, sock[s], ff[f], chip, rt, sl, mx, m2, sata))
    for b, n, rt, gb, mods, mhz, pr in RAMS:
        pid = add_product("RAM", b, n, f"{rt}-{mhz}, {gb} GB kit ({mods} module{'s' if mods > 1 else ''})", pr)
        cur.execute("INSERT INTO ram VALUES (?,?,?,?,?)", (pid, rt, gb, mods, mhz))
    for b, n, chip, vram, ln, tdp, minpsu, pr in GPUS:
        pid = add_product("GPU", b, n, f"{chip}, {vram} GB VRAM, {ln} mm long, {tdp} W, PSU {minpsu} W or more", pr)
        cur.execute("INSERT INTO gpu VALUES (?,?,?,?,?,?)", (pid, chip, vram, ln, tdp, minpsu))
    for b, n, w, eff, mod, pr in PSUS:
        pid = add_product("PSU", b, n, f"{w} W, {eff}, {mod.lower()} modular", pr)
        cur.execute("INSERT INTO psu VALUES (?,?,?,?)", (pid, w, eff, mod))
    for b, n, gl, ch, forms, pr in CASES:
        pid = add_product("Case", b, n, f"Fits {', '.join(forms)}; GPU up to {gl} mm; cooler up to {ch} mm", pr)
        cur.execute("INSERT INTO pc_case VALUES (?,?,?)", (pid, gl, ch))
        for f in forms:
            cur.execute("INSERT INTO case_form_factor VALUES (?,?)", (pid, ff[f]))
    for b, n, t, cap, pr in STORAGE:
        pid = add_product("Storage", b, n, f"{t}, {cap} GB", pr)
        cur.execute("INSERT INTO storage VALUES (?,?,?)", (pid, t, cap))
    for b, n, t, h, tdp, socks, pr in COOLERS:
        pid = add_product("Cooler", b, n, f"{t} cooler, {h} mm tall, up to {tdp} W, sockets {', '.join(socks)}", pr)
        cur.execute("INSERT INTO cooler VALUES (?,?,?,?)", (pid, t, h, tdp))
        for s in socks:
            cur.execute("INSERT INTO cooler_socket VALUES (?,?)", (pid, sock[s]))

    # stores and users
    store_rows = [(cur.execute("INSERT INTO stores(name, website) VALUES (?,?)", s).lastrowid, s[1]) for s in STORES]
    admin_ids = [cur.execute("INSERT INTO users(username, email, role) VALUES (?,?,'admin')", a).lastrowid
                 for a in ADMINS]
    used = set()
    for _ in range(N_CUSTOMERS):
        while True:
            fn, ln = rng.choice(FIRST), rng.choice(LAST)
            uname = f"{fn}.{ln}{rng.randint(1, 99)}".lower()
            if uname not in used:
                used.add(uname)
                break
        cur.execute("INSERT INTO users(username, email, role) VALUES (?,?,'customer')",
                    (uname, f"{uname}@example.com"))

    # listings: each product is sold by 1-6 stores at slightly different prices
    for pid, price in base_price.items():
        picks = rng.sample(store_rows, rng.choices([1, 2, 3, 4, 5, 6], [10, 20, 25, 20, 15, 10])[0])
        avail = [rng.choices(["in_stock", "out_of_stock", "preorder"], [72, 20, 8])[0] for _ in picks]
        if "in_stock" not in avail:
            avail[0] = "in_stock"                       # every product can be bought somewhere
        for (sid, site), av in zip(picks, avail):
            stamp = dt.datetime.combine(TODAY, dt.time(12)) - dt.timedelta(days=rng.randint(0, 30),
                                                                           minutes=rng.randint(0, 600))
            name = cur.execute("SELECT name FROM products WHERE product_id = ?", (pid,)).fetchone()[0]
            cur.execute("INSERT INTO listings(product_id, store_id, created_by_user_id, price, availability, "
                        "product_url, last_updated) VALUES (?,?,?,?,?,?,?)",
                        (pid, sid, rng.choice(admin_ids), round(price * rng.uniform(0.9, 1.12), 2), av,
                         f"{site}/p/{slug(name)}-{pid}", stamp.strftime("%Y-%m-%d %H:%M:%S")))

    # builds
    def rows(sql):
        return [dict(r) for r in cur.execute(sql)]

    cpus = rows("SELECT * FROM cpu")
    mbs = rows("SELECT * FROM motherboard")
    rams = rows("SELECT * FROM ram")
    gpus = rows("SELECT * FROM gpu")
    psus = rows("SELECT * FROM psu")
    cases = rows("SELECT * FROM pc_case")
    stos = rows("SELECT * FROM storage")
    cools = rows("SELECT * FROM cooler")
    case_ff = {}
    for r in cur.execute("SELECT * FROM case_form_factor"):
        case_ff.setdefault(r["product_id"], set()).add(r["form_factor_id"])
    cool_sock = {}
    for r in cur.execute("SELECT * FROM cooler_socket"):
        cool_sock.setdefault(r["product_id"], set()).add(r["socket_id"])

    def make_valid():
        for _ in range(200):
            cpu = rng.choice(cpus)
            mb_opts = [m for m in mbs if m["socket_id"] == cpu["socket_id"]]
            mb = rng.choice(mb_opts)
            ram_opts = [r for r in rams if r["ram_type"] == mb["ram_type"]
                        and r["modules"] <= mb["ram_slots"] and r["capacity_gb"] <= mb["max_ram_gb"]]
            case_opts = [c for c in cases if mb["form_factor_id"] in case_ff[c["product_id"]]]
            if not ram_opts or not case_opts:
                continue
            ram, case = rng.choice(ram_opts), rng.choice(case_opts)
            gpu = None
            if rng.random() < 0.85:
                g_opts = [g for g in gpus if g["length_mm"] <= case["max_gpu_length_mm"]]
                gpu = rng.choice(g_opts) if g_opts else None
            need = cpu["tdp_w"] + (gpu["tdp_w"] if gpu else 0) + 100
            if gpu:
                need = max(need, gpu["min_psu_w"])
            psu_opts = [p for p in psus if p["wattage"] >= need]
            if not psu_opts:
                continue
            cooler = None
            if rng.random() < 0.8:
                k_opts = [k for k in cools if cpu["socket_id"] in cool_sock[k["product_id"]]
                          and k["height_mm"] <= case["max_cooler_height_mm"] and k["max_tdp_w"] >= cpu["tdp_w"]]
                cooler = rng.choice(k_opts) if k_opts else None
            nvme = [s for s in stos if s["storage_type"] == "NVMe SSD"]
            sata = [s for s in stos if s["storage_type"] != "NVMe SSD"]
            drives = {rng.choice(nvme)["product_id"]}
            if rng.random() < 0.4:
                drives.add(rng.choice(sata)["product_id"])
            parts = {"CPU": [cpu["product_id"]], "Motherboard": [mb["product_id"]], "RAM": [ram["product_id"]],
                     "PSU": [rng.choice(psu_opts)["product_id"]], "Case": [case["product_id"]],
                     "Storage": sorted(drives)}
            if gpu:
                parts["GPU"] = [gpu["product_id"]]
            if cooler:
                parts["Cooler"] = [cooler["product_id"]]
            return parts
        raise RuntimeError("could not make a valid build")

    by_id = {r["product_id"]: r for r in cpus + mbs + rams + gpus + psus + cases + stos + cools}

    def break_build(parts):
        """Replace one part so that exactly one kind of incompatibility is introduced."""
        kinds = ["socket", "ram_type", "form", "gpu_len", "psu", "cooler_h", "m2", "ram_slots",
                 "cooler_s", "cooler_tdp"]
        rng.shuffle(kinds)
        cpu, mb, case = (by_id[parts[k][0]] for k in ("CPU", "Motherboard", "Case"))
        for kind in kinds:
            if kind == "socket":
                opts, cat_ = [c for c in cpus if c["socket_id"] != cpu["socket_id"]], "CPU"
            elif kind == "ram_type":
                opts, cat_ = [r for r in rams if r["ram_type"] != mb["ram_type"]], "RAM"
            elif kind == "form":
                opts, cat_ = [c for c in cases if mb["form_factor_id"] not in case_ff[c["product_id"]]], "Case"
            elif kind == "gpu_len":
                opts, cat_ = [g for g in gpus if g["length_mm"] > case["max_gpu_length_mm"]], "GPU"
            elif kind == "psu":
                gpu = by_id[parts["GPU"][0]] if "GPU" in parts else None
                need = cpu["tdp_w"] + (gpu["tdp_w"] if gpu else 0) + 100
                if gpu:
                    need = max(need, gpu["min_psu_w"])
                opts, cat_ = [p for p in psus if p["wattage"] < need], "PSU"
            elif kind == "cooler_h":
                opts, cat_ = [k for k in cools if k["height_mm"] > case["max_cooler_height_mm"]], "Cooler"
            elif kind == "cooler_s":
                opts, cat_ = [k for k in cools if cpu["socket_id"] not in cool_sock[k["product_id"]]], "Cooler"
            elif kind == "cooler_tdp":
                opts, cat_ = [k for k in cools if k["max_tdp_w"] < cpu["tdp_w"]], "Cooler"
            elif kind == "ram_slots":
                opts, cat_ = [r for r in rams if r["ram_type"] == mb["ram_type"]
                              and r["modules"] > mb["ram_slots"]], "RAM"
            else:  # m2: more NVMe drives than M.2 slots
                nvme = [s["product_id"] for s in stos if s["storage_type"] == "NVMe SSD"]
                if mb["m2_slots"] + 1 <= len(nvme):
                    parts["Storage"] = rng.sample(nvme, mb["m2_slots"] + 1)
                    return
                continue
            if opts:
                parts[cat_] = [rng.choice(opts)["product_id"]]
                return

    cust_ids = [r[0] for r in cur.execute("SELECT user_id FROM users WHERE role = 'customer'")]
    for i in range(N_BUILDS):
        parts = make_valid()
        roll = rng.random()
        if roll < 0.30:      # introduce one incompatibility
            break_build(parts)
        elif roll < 0.38:    # leave a required part out
            parts.pop(rng.choice(["PSU", "Case", "Storage", "RAM"]))
        bid = cur.execute("INSERT INTO builds(user_id,name,created_at) VALUES (?,?,?)",
                          (rng.choice(cust_ids), rng.choice(BUILD_NAMES),
                           (TODAY - dt.timedelta(days=rng.randint(0, 300))).isoformat())).lastrowid
        for plist in parts.values():
            for pid in plist:
                cur.execute("INSERT INTO build_items(build_id,product_id,quantity) VALUES (?,?,1)", (bid, pid))

    con.commit()

    # summary
    print("Database written to", DB_PATH)
    for t in ["categories", "products", "stores", "users", "listings", "cpu", "motherboard", "ram", "gpu", "psu",
              "pc_case", "storage", "cooler", "builds", "build_items"]:
        print(f"  {t:14s}{con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>6d} rows")
    bad = con.execute("SELECT COUNT(DISTINCT build_id) FROM v_build_issues WHERE severity='ERROR'").fetchone()[0]
    warn = con.execute("SELECT COUNT(DISTINCT build_id) FROM v_build_issues WHERE severity='WARNING'").fetchone()[0]
    print(f"  builds with compatibility errors: {bad}, with missing parts: {warn}")
    print("  foreign key violations:", len(con.execute("PRAGMA foreign_key_check").fetchall()))
    con.close()


if __name__ == "__main__":
    main()
