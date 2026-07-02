"""
Data access layer for TrackMySpend.

Upgrades over the original app1.py:
- Budgets are now persisted per user/month (previously reset on every rerun).
- Edit/delete now operate on the row `id`, not merchant name (previously two
  expenses from the same merchant were indistinguishable and editing/deleting
  one could silently affect the wrong row).
- Passwords are migrated to bcrypt transparently on login (see auth.py).
"""
import sqlite3
import pandas as pd
from contextlib import contextmanager

import config
from auth import hash_password, verify_password, is_bcrypt_hash

@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_FILE)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            merchant TEXT,
            date TEXT,
            total REAL,
            category TEXT,
            description TEXT
        )
        """)
        # New: persisted monthly budgets, one row per user+month
        c.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER,
            month TEXT,
            amount REAL,
            PRIMARY KEY (user_id, month)
        )
        """)
        conn.commit()

# ---------- Users ----------

def register_user(username: str, password: str) -> bool:
    try:
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                      (username, hash_password(password)))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username: str, password: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if not row:
            return None
        user_id, stored_hash = row
        if not verify_password(password, stored_hash):
            return None
        # Transparent migration: upgrade legacy sha256 hashes to bcrypt
        if not is_bcrypt_hash(stored_hash):
            c.execute("UPDATE users SET password=? WHERE id=?", (hash_password(password), user_id))
            conn.commit()
        return user_id

def get_username(user_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
        return row[0] if row else "Unknown"

# ---------- Expenses ----------

def save_expense(user_id, merchant, date, total, category, description):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO expenses (user_id, merchant, date, total, category, description)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (user_id, merchant, str(date), total, category, description))
        conn.commit()

def load_expenses(user_id) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC", conn, params=(user_id,))

def update_expense(expense_id, merchant, total, category):
    """Fixed: now keyed on the unique row id, not merchant name."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE expenses SET merchant=?, total=?, category=? WHERE id=?",
                  (merchant, total, category, expense_id))
        conn.commit()

def delete_expense(expense_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        conn.commit()

# ---------- Budgets (new) ----------

def get_budget(user_id, month: str) -> float:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT amount FROM budgets WHERE user_id=? AND month=?", (user_id, month))
        row = c.fetchone()
        return row[0] if row else 0.0

def set_budget(user_id, month: str, amount: float):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO budgets (user_id, month, amount) VALUES (?, ?, ?)
                     ON CONFLICT(user_id, month) DO UPDATE SET amount=excluded.amount""",
                  (user_id, month, amount))
        conn.commit()
