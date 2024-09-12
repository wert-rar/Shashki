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
    cur.execute('SELECT login FROM player WHERE login = "?"', (user_login,))
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


def find_waiting_game():
    with connect_db() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM game WHERE status = 'waiting' AND (white_user IS NULL OR black_user IS NULL)")
        return cur.fetchone()


def update_game_with_user(game_id, user_login, color):
    with connect_db() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        if color == 'white':
            cur.execute("UPDATE game SET white_user = ?, status = 'active' WHERE game_id = ?", (user_login, game_id))
        else:
            cur.execute("UPDATE game SET black_user = ?, status = 'active' WHERE game_id = ?", (user_login, game_id))
        con.commit()


def create_new_game(user_login):
    with connect_db() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO game (status, white_user, black_user, start_time) VALUES ('waiting', ?, NULL, CURRENT_TIMESTAMP)",
            (user_login,))
        con.commit()
        return cur.lastrowid


def get_game_status(game_id):
    with connect_db() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT status FROM game WHERE game_id = ?", (game_id,))
        return cur.fetchone()


def get_pieces_and_current_player(game_id):
    con = sqlite3.connect("DataBase.db")
    cur = con.cursor()

    cur.execute("SELECT white_user, black_user FROM game WHERE game_id = ?", (game_id,))
    game = cur.fetchone()
    if game:
        white_user, black_user = game
        return white_user, black_user
    return None


def get_user_color(game_id, user_id):
    con = sqlite3.connect("DataBase.db")
    cur = con.cursor()

    cur.execute("SELECT id FROM player WHERE user_id = ?", (user_id,))
    user_login = cur.fetchone()
    if user_login:
        user_login = user_login[0]

        cur.execute("SELECT white_user, black_user FROM game WHERE game_id = ?", (game_id,))
        game = cur.fetchone()

        if game:
            white_user, black_user = game
            if white_user == user_login:
                return 'white'
            elif black_user == user_login:
                return 'black'
    return None


if __name__ == "__main__":
    create_tables()
    input_login = input("Введите логин пользователя: ")
    input_password = input("Введите пароль пользователя: ")
    register_user(input_login, input_password)
