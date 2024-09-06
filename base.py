import sqlite3

con = sqlite3.connect("DataBase.db")
cur = con.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS player(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE,
        password TEXT,
        rang BIGINT,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    )
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS game(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT
    )
""")

cur.execute("SELECT COUNT(*) FROM game")
if cur.fetchone()[0] == 0:
    cur.execute("INSERT INTO game (status) VALUES ('waiting')")
    con.commit()

user_login = input('Login: ')
user_password = input('Password: ')

cur.execute("SELECT login FROM player WHERE login = ?", (user_login,))
if cur.fetchone() is None:
    cur.execute(
        "INSERT INTO player (login, password, rang, wins, losses) VALUES (?, ?, ?, ?, ?)",
        (user_login, user_password, 0, 0, 0)
    )
    con.commit()
    print('Пользователь успешно зарегистрирован!')
else:
    print('Такой пользователь уже зарегистрирован!')

con.close()
