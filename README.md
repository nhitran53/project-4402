# PC Parts Price Comparison

Our CSC 4402 project. It's a database of PC parts and the prices different online stores charge for them.
You can look up a part, see which store has it cheapest, and put together a PC build. The program checks
whether the parts in a build actually work together (right socket, enough power, GPU fits in the case, etc.).

It's written in Python 3 with SQLite, so there's nothing to install besides Python.

## Running it

You need Python 3.8 or newer. Open a terminal in this folder and run:

```
python app.py
```

(On Mac/Linux it might be `python3` instead of `python`.)

The database `pcparts.db` is already included and filled with sample data, so the app works right away.

To run our test queries:

```
python test_queries.py    # the 5 test queries from the report
python test_rules.py      # tests for the compatibility rules and triggers
```

`test_rules.py` works on a copy of the database in memory, so it doesn't change anything.

If you mess up the data while trying things out, run `python generate_data.py` to rebuild the database
from scratch. It always produces the same data.

## Using the app

When you start it you pick one of five screens. There are no passwords. You just log in with a username.

1. **Product Search**: search for parts, browse a category with a price limit, and see a part's specs
   and prices. Try logging in as `linda.johnson95`, or type `NEW` to make an account.
2. **Price Comparison and PC Builder**: compare store prices and create or edit builds. The app shows
   the total cost and any compatibility problems. `carlos.anderson88` has a build (#59) with some
   problems in it, if you want to see what that looks like.
3. **Product Management** (admin): add, edit and delete products.
4. **Listing Management** (admin): add, update and delete store prices, and find ones that are out of date.
5. **Store Management** (admin): manage stores and user accounts.

For the admin screens, log in as `dwhitfield`.

When searching, you don't need the exact name. Typing a few words like `asus 4070` or `samsung 990`
works, and it can handle small typos too. Wherever the app asks for a product, you can type its id
or part of its name.

## Files

- `schema.sql`: all the tables, constraints, triggers and views
- `generate_data.py`: creates `pcparts.db` and fills it with sample data
- `queries.sql` / `test_queries.py`: our 5 test queries
- `test_rules.py`: extra tests
- `app.py`: the main menu
- `search_ui.py`, `compare_ui.py`, `product_ui.py`, `listing_ui.py`, `store_ui.py`: the five screens
- `db.py`, `catalog.py`: shared code used by the screens

## Database design

The main tables come from our ER diagram: `categories`, `products`, `stores`, `users` and `listings`.
A listing is one store's price for one product. We also added a spec table for each type of part
(cpu, gpu, ram, ...) and `builds` / `build_items` for saved PC builds.

The compatibility check is a view called `v_build_issues`. It has one query for each of our 13 rules
and lists every problem in every build. Problems are marked as either an error or a warning (a warning
means a required part is missing). `v_best_price` finds the cheapest in-stock price for each product,
and `v_build_total` uses it to price a build.

When you add a part to a build, the app tries each possible part inside a transaction, checks whether
it causes new errors, and then rolls it back. That way it only suggests parts that fit.

Some rules are enforced with triggers:
- only admins can add listings
- a listing's `last_updated` time updates automatically when it changes
- a spec row has to match the product's category (e.g. you can't give a CPU a GPU spec)
- a build can only have one of each single-slot part (one CPU, one motherboard, etc.)

## Notes

All the data is made up. The product names are real, but the specs and prices are only approximate.
Store websites use `.example` addresses so they don't point anywhere real.
