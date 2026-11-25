"""Database connection plus input/output helpers used by every screen."""
import contextlib
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PCPARTS_DB") or os.path.join(HERE, "pcparts.db")


class Quit(Exception):
    """Raised when the input stream ends (Ctrl-D) so the app can exit cleanly."""


class UserError(Exception):
    """A problem the user can fix (bad input, rule broken). Shown as a plain message."""


def connect():
    if not os.path.exists(DB_PATH):
        sys.exit(f"Database not found at {DB_PATH}\nCreate it with: python3 backend/generate_data.py")
    con = sqlite3.connect(DB_PATH, isolation_level=None)   # autocommit; tx() groups statements
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextlib.contextmanager
def tx(con):
    """All-or-nothing group of statements."""
    con.execute("BEGIN")
    try:
        yield
    except BaseException:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")


# input helpers
def ask(prompt, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    try:
        s = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        raise Quit()
    if s:
        return s
    return "" if default is None else str(default)


def _ask_number(prompt, cast, lo, hi, default, blank_ok):
    while True:
        s = ask(prompt, default)
        if s == "" and blank_ok:
            return None
        try:
            v = cast(s)
        except ValueError:
            print("  Please enter a number.")
            continue
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            print(f"  Value must be between {lo if lo is not None else '-inf'} and {hi if hi is not None else 'inf'}.")
            continue
        return v


def ask_int(prompt, lo=None, hi=None, default=None, blank_ok=False):
    return _ask_number(prompt, int, lo, hi, default, blank_ok)


def ask_float(prompt, lo=None, hi=None, default=None, blank_ok=False):
    return _ask_number(prompt, float, lo, hi, default, blank_ok)


def ask_required(prompt, default=None):
    while True:
        s = ask(prompt, default)
        if s:
            return s
        print("  This field is required.")


def confirm(prompt, default=False):
    s = ask(f"{prompt} ({'Y/n' if default else 'y/N'})").lower()
    if not s:
        return default
    return s in ("y", "yes")


def ask_choice(prompt, options, default=None):
    """options: list of strings. Returns the chosen string."""
    while True:
        s = ask(f"{prompt} ({'/'.join(options)})", default)
        for o in options:
            if s.lower() == o.lower():
                return o
        print("  Choose one of:", ", ".join(options))


# output helpers
def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def table(rows, headers=None):
    rows = list(rows)
    if not rows:
        print("  (no rows)")
        return
    if headers is None:
        headers = list(rows[0].keys())
    cells = [[_fmt(v) for v in tuple(r)] for r in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    print("  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for r in cells:
        print("  " + "  ".join(v.ljust(w) for v, w in zip(r, widths)))
    print(f"  ({len(cells)} row{'s' if len(cells) != 1 else ''})")


def money(v):
    return f"${v:,.2f}"


def menu(title, options, back_label="Back"):
    """options: list of (label, function).  Loops until the user picks 0."""
    while True:
        print(f"\n=== {title} ===")
        for i, (label, _) in enumerate(options, 1):
            print(f"  {i}. {label}")
        print(f"  0. {back_label}")
        choice = ask("Choose")
        if choice == "0":
            return
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            try:
                options[int(choice) - 1][1]()
            except UserError as e:
                print(f"\n! {e}")
            except sqlite3.Error as e:
                print(f"\n! The database refused that change: {e}")
        else:
            print("  Invalid choice.")
