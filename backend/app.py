#!/usr/bin/env python3
"""
Main program. Run with: python app.py

Logs the user in and shows the main menu. Options 1-2 are for everyone,
3-5 are for admins.
"""
import compare_ui
import listing_ui
import product_ui
import search_ui
import store_ui
from db import Quit, UserError, ask_required, connect, menu, table


def find_user(con, who):
    return con.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE OR username = ? COLLATE NOCASE",
                       (who, who)).fetchone()


def login(con, admin_only=False):
    if admin_only:
        print("\nAdministrator sign-in. Demo administrators:")
        table(con.execute("SELECT username, email FROM users WHERE role = 'admin' ORDER BY user_id"))
    else:
        ex = con.execute("SELECT username FROM users WHERE role = 'customer' ORDER BY user_id LIMIT 1").fetchone()[0]
        print(f"\nSign in with your username or e-mail (for example {ex}), or type NEW to register.")
    who = ask_required("Username or e-mail")
    if who.lower() == "new" and not admin_only:
        uname, email = ask_required("Choose a username"), ask_required("E-mail")
        con.execute("INSERT INTO users(username, email, role) VALUES (?,?, 'customer')", (uname, email))
        who = uname
        print("  Account created.")
    u = find_user(con, who)
    if u is None:
        raise UserError("No such user.")
    if admin_only and u["role"] != "admin":
        raise UserError("This screen is for administrators only.")
    return u


def main():
    con = connect()
    print("=" * 62)
    print("  PC COMPONENT PRICE COMPARISON  --  with compatibility checks")
    print("=" * 62)
    try:
        menu("Main menu", [
            ("Product Search", lambda: search_ui.run(con, login(con))),
            ("Price Comparison and PC Builder", lambda: compare_ui.run(con, login(con))),
            ("Product Management (admin)", lambda: product_ui.run(con, login(con, True))),
            ("Listing Management (admin)", lambda: listing_ui.run(con, login(con, True))),
            ("Store and User Management (admin)", lambda: store_ui.run(con, login(con, True))),
        ], back_label="Exit")
    except (Quit, KeyboardInterrupt):
        pass
    print("\nGoodbye.")


if __name__ == "__main__":
    main()
