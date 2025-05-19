import sqlite3
import datetime

DB_NAME = "clients.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS clients (
                        phone TEXT PRIMARY KEY,
                        birth_date TEXT,
                        email TEXT,
                        acc_pass TEXT,
                        mail_pass TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
                        phone TEXT,
                        type TEXT,
                        months INTEGER,
                        start_date TEXT,
                        end_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS games (
                        phone TEXT,
                        name TEXT)''')
        conn.commit()

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
        line = lines[i]
        if line.strip() == "---":
            i += 1
            continue
        if section == 'subs' and (i+1 < len(lines) and lines[i+1].strip() != "---"):
            sub_line = line.strip()
            date_line = lines[i+1].strip()
            if sub_line.endswith("м"):
                typ = ' '.join(sub_line.split()[:-1])
                months = int(sub_line.split()[-1].replace("м", ""))
                start_date = datetime.datetime.strptime(date_line, "%d.%m.%Y")
                end_date = start_date + datetime.timedelta(days=months*30)
                subs.append((typ, months, start_date.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y")))
                i += 2
                continue
        section = 'games'
        games.append(line.strip())
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

def get_client_block(phone):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        client = c.fetchone()
        if not client:
            return None
        text = "\n".join(client)
        c.execute("SELECT type, months, start_date FROM subscriptions WHERE phone = ?", (phone,))
        subs = c.fetchall()
        for s in subs:
            text += f"\n---\n{s[0]} {s[1]}м\n{s[2]}"
        c.execute("SELECT name FROM games WHERE phone = ?", (phone,))
        games = c.fetchall()
        if games:
            text += "\n---\n" + "\n".join(g[0] for g in games)
        return text

def get_upcoming_notifications():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        today = datetime.datetime.now().strftime("%d.%m.")
        c.execute("SELECT phone, type, months, end_date FROM subscriptions WHERE end_date = ?", (tomorrow,))
        subs = c.fetchall()
        c.execute("SELECT phone, birth_date FROM clients")
        bdays = [(p, b) for p, b in c.fetchall() if b.endswith(today)]
        return [(s[0], s[1], s[2], s[3], None) for s in subs] + [(b[0], "", "", "", b[1]) for b in bdays]