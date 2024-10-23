import sqlite3


def create_tables():
    con = sqlite3.connect("DataBase.db")
    cur = con.cursor()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS player(
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE,
                    password TEXT,
                    rang BIGINT,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0
                )
            """)

    cur.execute("""
                CREATE TABLE IF NOT EXISTS game(
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT,
                    white_user TEXT,
                    black_user TEXT,
                    start_time TIMESTAMP,
                    FOREIGN KEY (white_user) REFERENCES player(login),
                    FOREIGN KEY (black_user) REFERENCES player(login)
                )
            """)

    con.commit()

    cur.execute("PRAGMA table_info(game)")
    columns = [column[1] for column in cur.fetchall()]
    if 'start_time' not in columns:
        cur.execute("ALTER TABLE game ADD COLUMN start_time TIMESTAMP")

    cur.execute("SELECT COUNT(*) FROM game")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO game (status, white_user, black_user) VALUES ('waiting', NULL, NULL)")
        con.commit()

    con.close()


def connect_db():
    con = sqlite3.connect('../DataBase.db')
    con.row_factory = sqlite3.Row
    return con


def check_user_exists(user_login):
    con = connect_db()
    cur = con.cursor()
    cur.execute('SELECT login FROM player WHERE login = ?', (user_login,))
    exists = cur.fetchone() is not None
    con.close()
    return exists


def register_user(user_login, user_password):
    con = connect_db()
    cur = con.cursor()
    cur.execute("INSERT INTO player (login, password, rang) VALUES (?, ?, ?)", (user_login, user_password, 0))
    con.commit()
    con.close()


def authenticate_user(user_login, user_password):
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM player WHERE login = ? AND password = ?", (user_login, user_password))
    user = cur.fetchone()
    con.close()
    return user


def get_user_by_login(username):
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM player WHERE login = ?", (username,))
    user = cur.fetchone()
    con.close()
    return user


if __name__ == "__main__":
    create_tables()
    input_login = input("Введите логин пользователя: ")
    input_password = input("Введите пароль пользователя: ")
    register_user(input_login, input_password)
