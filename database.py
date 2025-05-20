import sqlite3

def init_db():
    conn = sqlite3.connect("clients.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        phone TEXT,
        birth_date TEXT,
        email TEXT,
        account_password TEXT,
        email_password TEXT,
        subscription_name TEXT,
        subscription_term TEXT,
        subscription_region TEXT,
        subscription_start TEXT,
        subscription_end TEXT,
        games TEXT
    )
    """)
    conn.commit()
    conn.close()