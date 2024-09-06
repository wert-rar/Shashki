import sqlite3

def create_tables():
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_user(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_login TEXT,
            FOREIGN KEY (game_id) REFERENCES game(id),
            FOREIGN KEY (user_login) REFERENCES player(login)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS moves(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_login TEXT,
            move TEXT,
            FOREIGN KEY (game_id) REFERENCES game(id),
            FOREIGN KEY (user_login) REFERENCES player(login)
        )
    """)

    cur.execute("SELECT COUNT(*) FROM game")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO game (status) VALUES ('waiting')")
        con.commit()

    con.close()

def register_user():
    con = sqlite3.connect("DataBase.db")
    cur = con.cursor()

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

if __name__ == "__main__":
    create_tables()
    register_user()
