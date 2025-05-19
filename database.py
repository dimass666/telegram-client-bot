import sqlite3
import datetime
import pyAesCrypt
import os

DB_NAME = "clients.db"
ENCRYPTED_DB_NAME = "clients_encrypted.db"
ENCRYPTION_PASSWORD = "57131702"
BUFFER_SIZE = 64 * 1024

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS clients (phone TEXT PRIMARY KEY, birth_date TEXT, email TEXT, acc_pass TEXT, mail_pass TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS subscriptions (phone TEXT, type TEXT, months INTEGER, start_date TEXT, end_date TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS games (phone TEXT, name TEXT)")
        conn.commit()

def encrypt_database():
    if os.path.exists(DB_NAME):
        pyAesCrypt.encryptFile(DB_NAME, ENCRYPTED_DB_NAME, ENCRYPTION_PASSWORD, BUFFER_SIZE)

def parse_block(lines):
    phone = lines[0]
    birth_date = lines[1]
    email = lines[2]
    acc_pass = lines[3]
    mail_pass = lines[4]

    subs = []
    games = []
    i = 5
    while i < len(lines):
        line = lines[i].strip()
        if line == "---":
            i += 1
            break
        try:
            parts = line.split()
            name = " ".join(parts[:-2])
            months = int(parts[-2].replace("м", ""))
            region = parts[-1]
            start_date = datetime.datetime.strptime(lines[i + 1], "%d.%m.%Y")
            end_date = start_date + datetime.timedelta(days=30 * months)
            subs.append((f"{name} {months}м {region}", months, start_date.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y")))
            i += 2
        except:
            i += 1

    while i < len(lines):
        games.append(lines[i].strip())
        i += 1

    return phone, birth_date, email, acc_pass, mail_pass, subs, games

def save_client_block(lines):
    phone, birth, email, acc_pass, mail_pass, subs, games = parse_block(lines)
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        c.execute("DELETE FROM subscriptions WHERE phone = ?", (phone,))
        c.execute("DELETE FROM games WHERE phone = ?", (phone,))
        c.execute("INSERT INTO clients VALUES (?, ?, ?, ?, ?)", (phone, birth, email, acc_pass, mail_pass))
        for sub in subs:
            c.execute("INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?)", (phone, *sub))
        for g in games:
            c.execute("INSERT INTO games VALUES (?, ?)", (phone, g))
        conn.commit()
    encrypt_database()

def get_client_block(phone):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        row = c.fetchone()
        if not row:
            return None
        phone, birth, email, acc_pass, mail_pass = row
        result = f"{phone}\n{birth}\n{email}\n{acc_pass}\n{mail_pass}"
        c.execute("SELECT type, months, start_date, end_date FROM subscriptions WHERE phone = ?", (phone,))
        subs = c.fetchall()
        for sub in subs:
            result += f"\n{sub[0]}\n{sub[2]}\nАктивна до: {sub[3]}"
        c.execute("SELECT name FROM games WHERE phone = ?", (phone,))
        games = c.fetchall()
        if games:
            result += "\n---\n" + "\n".join([g[0] for g in games])
        return result

def get_upcoming_notifications():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        today = datetime.datetime.now().strftime("%d.%m.")
        c.execute("SELECT phone, type, months, end_date FROM subscriptions WHERE end_date = ?", (tomorrow,))
        subs = [s for s in c.fetchall()]
        c.execute("SELECT phone, birth_date FROM clients")
        bdays = [(p, b) for p, b in c.fetchall() if b.endswith(today)]
        return [(s[0], s[1], s[2], s[3], None) for s in subs] + [(b[0], "", "", "", b[1]) for b in bdays]
