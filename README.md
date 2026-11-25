# PC Parts Price Comparison

CSC 4402 Database Management Systems project at Louisiana State University. Browse PC parts, compare store prices, and check whether a build is compatible. The React interface and terminal app share the same SQLite database.

## Run the website

Use Python 3.8+ and Node.js 20.19 or later in the 20.x series, or 22.12 or later, with npm. From the repository root:

```sh
npm --prefix frontend ci
npm --prefix frontend run build
python3 backend/server.py
```

Open [http://localhost:8000](http://localhost:8000). The sample database is included, and the server uses only Python’s standard library.

For frontend development, start the API and Vite in separate terminals:

```sh
# Terminal 1
python3 backend/server.py

# Terminal 2
npm --prefix frontend run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies API requests to port 8000. Set `PORT` and `API_URL` on the server and Vite respectively to use another port. Set `PCPARTS_DB` for the server or terminal app to use a separate database file.

## Try the main workflows

- **Build** lets you choose and replace parts, adjust memory and storage quantities, and review compatibility and estimated power.
- **Browse parts** supports name, brand, or model search and filters by category, price, stock, store, and specifications. Open a product to compare its store offers.
- **My builds** lets you save and reopen builds. Sign in as `linda.johnson95` to try it. For a build with compatibility issues, sign in as `carlos.anderson88` and open **Esports Build**.
- **Admin** lets you manage products, listings, stores, and users. Sign in as `dwhitfield`. The demo uses usernames or email addresses without passwords.

Store prices, availability, and URLs are sample data. A draft can use a specific store offer. The database saves parts and quantities, so reopened builds use each part’s lowest in-stock price.

## Run the terminal app and database tests

```sh
python3 backend/app.py
python3 backend/test_queries.py
python3 backend/test_rules.py
```

The query script runs the five queries from the project report. The rules script tests compatibility, triggers, and constraints on an in-memory copy.

The terminal menu includes product search, price comparison and PC building, and admin screens for products, listings, stores, and users. Sign in with the same sample accounts as the website, or type `NEW` at the product search login prompt to create an account. Try a search like `asus 4070` or `samsung 990`.

To reset the bundled sample database, run `python3 backend/generate_data.py`. This replaces the bundled database, including any local edits and saved builds.

## Repository layout

- `frontend/` — React, Tailwind CSS, and Vite.
- `backend/` — Python API and terminal app, SQLite schema and sample data, and database tests.

## Database design

The main tables are `categories`, `products`, `stores`, `users`, and `listings`. A listing records one store’s price for one product. Category-specific tables store technical specifications. `builds` and `build_items` store saved parts lists.

The `v_build_issues` view evaluates 13 compatibility rules and reports errors or missing required parts. `v_best_price` finds the lowest in-stock offer, and `v_build_total` uses those prices to calculate build totals. The builder checks draft compatibility with a temporary build in a transaction and rolls it back after reading the view.

Triggers enforce admin-only listing creation, update listing timestamps, check that specifications match the product category, and allow only one part in each single-slot category.
