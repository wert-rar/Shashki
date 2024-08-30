import sqlite3

con = sqlite3.connect("DataBase.db")
cur = con.cursor()  # Для выполнения SQL-запросов

cur.execute("""CREATE TABLE IF NOT EXISTS player(
            login TEXT, 
            password TEXT, 
            rang BIGINT)""")

con.commit()

user_login = input('Login: ')
user_password = input('Password: ')

cur.execute("SELECT login FROM Player WHERE login = ?", (user_login,))
if cur.fetchone() is None:
    cur.execute("INSERT INTO Player VALUES (?, ?, ?)", (user_login, user_password, 0))
    con.commit()
    print('Пользователь успешно зарегистрирован!')
else:
    print('Такой пользователь уже зарегистрирован!')

    for value in cur.execute("SELECT * FROM player"):
        print(value)
