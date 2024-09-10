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
    register_user()