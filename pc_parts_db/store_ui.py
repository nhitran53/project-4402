"""Menu option 5: store and user management (admin only)."""
import sqlite3

from db import UserError, ask, ask_choice, ask_int, ask_required, confirm, menu, table


def run(con, admin):
    # stores
    def list_stores():
        table(con.execute("SELECT s.store_id AS id, s.name, s.website, COUNT(l.listing_id) AS listings "
                          "FROM stores s LEFT JOIN listings l ON l.store_id = s.store_id "
                          "GROUP BY s.store_id ORDER BY s.store_id"))

    def add_store():
        con.execute("INSERT INTO stores(name, website) VALUES (?,?)", (ask_required("Store name"), ask("Website") or None))
        print("  Store added.")

    def update_store():
        list_stores()
        sid = ask_int("Store id")
        s = con.execute("SELECT * FROM stores WHERE store_id = ?", (sid,)).fetchone()
        if s is None:
            raise UserError("No such store.")
        con.execute("UPDATE stores SET name = ?, website = ? WHERE store_id = ?",
                    (ask_required("Name", s["name"]), ask("Website", s["website"] or "") or None, sid))
        print("  Store updated.")

    def delete_store():
        list_stores()
        sid = ask_int("Store id to remove")
        if confirm("Remove this store?"):
            try:
                n = con.execute("DELETE FROM stores WHERE store_id = ?", (sid,)).rowcount
                print("  Store removed." if n else "  No such store.")
            except sqlite3.IntegrityError:
                raise UserError("This store still has listings. Delete or move those listings first.")

    # users
    def list_users():
        kw = ask("Search username or e-mail (blank = all)")
        table(con.execute("SELECT user_id AS id, username, email, role FROM users "
                          "WHERE username LIKE ? OR email LIKE ? ORDER BY user_id LIMIT 30", (f"%{kw}%",) * 2))

    def add_user():
        con.execute("INSERT INTO users(username, email, role) VALUES (?,?,?)",
                    (ask_required("Username"), ask_required("E-mail"), ask_choice("Role", ["customer", "admin"], "customer")))
        print("  User added.")

    def change_role():
        uid = ask_int("User id")
        if uid == admin["user_id"]:
            raise UserError("You cannot change your own role.")
        n = con.execute("UPDATE users SET role = ? WHERE user_id = ?",
                        (ask_choice("New role", ["customer", "admin"]), uid)).rowcount
        print("  Role changed." if n else "  No such user.")

    def delete_user():
        uid = ask_int("User id to delete")
        if uid == admin["user_id"]:
            raise UserError("You cannot delete your own account.")
        if confirm("Delete this user (their saved builds are deleted too)?"):
            try:
                n = con.execute("DELETE FROM users WHERE user_id = ?", (uid,)).rowcount
                print("  User deleted." if n else "  No such user.")
            except sqlite3.IntegrityError:
                raise UserError("This administrator created listings and cannot be deleted.")

    menu(f"Store and User Management - {admin['username']} (admin)", [
        ("List stores", list_stores),
        ("Add a store", add_store),
        ("Update a store", update_store),
        ("Remove a store", delete_store),
        ("Find users", list_users),
        ("Add a user", add_user),
        ("Change a user's role", change_role),
        ("Delete a user", delete_user),
    ], back_label="Back to main menu")
