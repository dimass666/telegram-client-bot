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

def delete_client(phone):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        c.execute("DELETE FROM subscriptions WHERE phone = ?", (phone,))
        c.execute("DELETE FROM games WHERE phone = ?", (phone,))
        conn.commit()

def clear_database():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM clients")
        c.execute("DELETE FROM subscriptions")
        c.execute("DELETE FROM games")
        conn.commit()