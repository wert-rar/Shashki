import os
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
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0
        )
    """)


    # Создание таблицы 'game'
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

    # Проверка и добавление столбца 'start_time'
    cur.execute("PRAGMA table_info(game)")
    columns = [column[1] for column in cur.fetchall()]
    if 'start_time' not in columns:
        cur.execute("ALTER TABLE game ADD COLUMN start_time TIMESTAMP")

    # Инициализация таблицы 'game', если она пуста
    cur.execute("SELECT COUNT(*) FROM game")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO game (status, white_user, black_user) VALUES ('waiting', NULL, NULL)")
        con.commit()
        print("Таблица 'game' инициализирована.")

    con.close()
    print("Новая база данных создана.")


# Подключение к базе данных
def connect_db():
    con = sqlite3.connect("DataBase.db")
    con.row_factory = sqlite3.Row
    return con


# Проверка существования пользователя
def check_user_exists(user_login):
    con = connect_db()
    cur = con.cursor()
    cur.execute('SELECT login FROM player WHERE login = ?', (user_login,))
    exists = cur.fetchone() is not None
    con.close()
    return exists


# Регистрация нового пользователя
def register_user(user_login, user_password):
    con = connect_db()
    cur = con.cursor()
    cur.execute("INSERT INTO player (login, password, rang) VALUES (?, ?, ?)", (user_login, user_password, 0))
    con.commit()
    con.close()


# Аутентификация пользователя
def authenticate_user(user_login, user_password):
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM player WHERE login = ? AND password = ?", (user_login, user_password))
    user = cur.fetchone()
    con.close()
    return user


# Получение информации о пользователе
def get_user_by_login(username):
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM player WHERE login = ?", (username,))
    user = cur.fetchone()
    con.close()
    return user


# Обновление рейтинга пользователя
def update_user_rank(user_login, points):
    con = connect_db()
    cur = con.cursor()
    cur.execute("UPDATE player SET rang = rang + ? WHERE login = ?", (points, user_login))
    con.commit()
    con.close()


# Обновление статистики пользователя
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