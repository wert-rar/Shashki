import sqlite3

# Подключение к базе данных
con = sqlite3.connect("DataBase.db")
cur = con.cursor()

# Удалите таблицу player, если она существует, чтобы обновить структуру
cur.execute("DROP TABLE IF EXISTS player")

# Создание таблицы с правильной структурой
cur.execute("""
    CREATE TABLE player(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE,
        password TEXT,
        rang BIGINT,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    )
""")

con.commit()

# Ваш существующий код для регистрации пользователя
user_login = input('Login: ')
user_password = input('Password: ')

cur.execute("SELECT login FROM player WHERE login = ?", (user_login,))
if cur.fetchone() is None:
    cur.execute("INSERT INTO player (login, password, rang, wins, losses) VALUES (?, ?, ?, ?, ?)", (user_login, user_password, 0, 0, 0))
    con.commit()
    print('Пользователь успешно зарегистрирован!')
else:
    print('Такой пользователь уже зарегистрирован!')

cur.execute("SELECT id, login, wins, losses, wins + losses as total_games FROM player")
for value in cur.fetchall():
    print(value)

con.close()
