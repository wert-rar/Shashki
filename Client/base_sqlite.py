import sqlite3
import logging
import os
import hashlib

def create_tables():
    try:
        with sqlite3.connect("../DataBase.db") as con:
            cur = con.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS player(
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE,
                    password TEXT,
                    rang BIGINT DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    draws INTEGER DEFAULT 0
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS completed_game(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_login TEXT,
                    game_id INTEGER,
                    date_start TEXT,
                    rating_before INTEGER,
                    rating_after INTEGER,
                    rating_change INTEGER,
                    result TEXT
                )
            """)

            logging.info("Функция create_tables завершена успешно.")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании таблиц: {e}")

def connect_db():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, 'DataBase.db')
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def check_user_exists(user_login):
    con = connect_db()
    cur = con.cursor()
    cur.execute('SELECT login FROM player WHERE login = ?', (user_login,))
    exists = cur.fetchone() is not None
    con.close()
    return exists

def register_user(user_login, user_password):
    if check_user_exists(user_login):
        logging.warning(f"Пользователь с логином '{user_login}' уже существует.")
        return False
    hashed_password = hash_password(user_password)
    try:
        con = connect_db()
        cur = con.cursor()
        cur.execute("INSERT INTO player (login, password, rang) VALUES (?, ?, ?)",
                    (user_login, hashed_password, 0))
        con.commit()
        con.close()
        logging.info(f"Пользователь '{user_login}' успешно зарегистрирован.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Ошибка при регистрации пользователя: {e}")
        return False

def authenticate_user(user_login, user_password):
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT password FROM player WHERE login = ?", (user_login,))
    row = cur.fetchone()
    con.close()
    if row:
        stored_password = row["password"]
        hashed_input_password = hash_password(user_password)
        if hashed_input_password == stored_password:
            logging.info(f"Пользователь '{user_login}' успешно аутентифицирован.")
            return True
        else:
            logging.warning(f"Неверный пароль для пользователя '{user_login}'.")
            return False
    else:
        logging.warning(f"Пользователь '{user_login}' не найден.")
        return False

def get_user_by_login(username):
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM player WHERE login = ?", (username,))
    user = cur.fetchone()
    con.close()
    return user

def get_user_rang(user_login):
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT rang FROM player WHERE login = ?", (user_login,))
    row = cur.fetchone()
    con.close()
    if row:
        return row['rang']
    return 0

def update_user_rank(user_login, points):
    con = connect_db()
    cur = con.cursor()
    cur.execute("UPDATE player SET rang = rang + ? WHERE login = ?", (points, user_login))
    con.commit()
    con.close()

def update_user_stats(user_login, wins=0, losses=0, draws=0):
    con = connect_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE player
        SET wins = wins + ?,
            losses = losses + ?,
            draws = draws + ?
        WHERE login = ?
    """, (wins, losses, draws, user_login))
    con.commit()
    con.close()

def insert_completed_game(user_login, game_id, date_start, rating_before, rating_after, rating_change, result):
    con = connect_db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO completed_game
        (user_login, game_id, date_start, rating_before, rating_after, rating_change, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_login, game_id, date_start, rating_before, rating_after, rating_change, result))
    con.commit()
    con.close()

def get_user_history(user_login):
    con = connect_db()
    cur = con.cursor()
    cur.execute("""
        SELECT *
        FROM completed_game
        WHERE user_login = ?
        ORDER BY id ASC
    """, (user_login,))
    rows = cur.fetchall()
    con.close()

    result = []
    for row in rows:
        result.append(dict(row))
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_tables()
