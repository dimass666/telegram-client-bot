import sqlite3

def init_db():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        birth_date TEXT,
        email TEXT,
        account_password TEXT,
        mail_password TEXT,
        subscription_name TEXT,
        subscription_start TEXT,
        subscription_end TEXT,
        region TEXT,
        games TEXT
    )''')
    conn.commit()
    conn.close()

def add_client(data):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute('''INSERT INTO clients (
        username, birth_date, email, account_password,
        mail_password, subscription_name, subscription_start,
        subscription_end, region, games
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()

def get_all_clients():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute("SELECT * FROM clients")
    result = c.fetchall()
    conn.close()
    return result