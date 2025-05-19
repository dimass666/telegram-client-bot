import sqlite3
import datetime
import pyAesCrypt
from collections import defaultdict

DB_NAME = "clients.db"
ENCRYPTED_DB_NAME = "clients_encrypted.db"
ENCRYPTION_PASSWORD = "57131702"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS clients (
            phone TEXT PRIMARY KEY,
            birth_date TEXT,
            email TEXT,
            acc_pass TEXT,
            mail_pass TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
            phone TEXT,
            type TEXT,
            months INTEGER,
            start_date TEXT,
            end_date TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS games (
            phone TEXT,
            name TEXT)""")
        conn.commit()

def encrypt_database():
    buffer_size = 64 * 1024
    pyAesCrypt.encryptFile(DB_NAME, ENCRYPTED_DB_NAME, ENCRYPTION_PASSWORD, buffer_size)

def parse_block(lines):
    phone = lines[0]
    birth_date = lines[1]
    email = lines[2]
    acc_pass = lines[3]
    mail_pass = lines[4]

    subs = []
    games = []
    section = 'subs'
    i = 5
    while i < len(lines):
        line = lines[i].strip()
        if line == "---":
            i += 1
            continue
        if section == 'subs' and (i + 1 < len(lines)):
            try:
                parts = line.rsplit(' ', 1)
                typ = parts[0]
                months = int(parts[1].replace("м", ""))
                start_date = datetime.datetime.strptime(lines[i + 1].strip(), "%d.%m.%Y")
                end_date = start_date + datetime.timedelta(days=months * 30)
                subs.append((typ, months, start_date.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y")))
                i += 2
                continue
            except:
                pass
        section = 'games'
        games.append(line)
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
        for s in subs:
            c.execute("INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?)", (phone, *s))
        for g in games:
            c.execute("INSERT INTO games VALUES (?, ?)", (phone, g))
        conn.commit()
    encrypt_database()

def get_client_block(phone):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        client = c.fetchone()
        if not client:
            return None
        phone, birth, email, acc_pass, mail_pass = client
        text = f"{phone}\n{birth}\n{email}\n{acc_pass}\n{mail_pass}"
        c.execute("SELECT type, months, start_date, end_date FROM subscriptions WHERE phone = ?", (phone,))
        subs = c.fetchall()
        for s in subs:
            text += f"\n{s[0]} {s[1]}м\n{s[2]}\nАктивна до: {s[3]}"
        c.execute("SELECT name FROM games WHERE phone = ?", (phone,))
        games = c.fetchall()
        if games:
            text += "\n" + "\n".join(g[0] for g in games)
        return text

def get_upcoming_notifications():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        today = datetime.datetime.now().strftime("%d.%m.")
        c.execute("SELECT phone, type, months, end_date FROM subscriptions WHERE end_date = ?", (tomorrow,))
        subs = [s for s in c.fetchall() if not any(x in s[1].lower() for x in ["нету", "закончилась"])]
        c.execute("SELECT phone, birth_date FROM clients")
        bdays = [(p, b) for p, b in c.fetchall() if b.endswith(today)]
        return [(s[0], s[1], s[2], s[3], None) for s in subs] + [(b[0], "", "", "", b[1]) for b in bdays]

def get_all_clients():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT phone FROM clients")
        return [row[0] for row in c.fetchall()]

def get_region_stats():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT type FROM subscriptions")
        regions = defaultdict(int)
        for row in c.fetchall():
            typ = row[0].lower()
            if "(тур)" in typ:
                regions["Турция"] += 1
            elif "(укр)" in typ:
                regions["Украина"] += 1
            else:
                regions["Другое"] += 1
        return regions