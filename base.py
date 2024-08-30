import sqlite3

con = sqlite3.connect("DataBase.db")
cur = con.cursor()  # Для выполнения SQL-запросов

cur.execute("CREATE TABLE IF NOT EXISTS Player("
            "login TEXT, "
            "password TEXT, "
            "rang BIGINT)")

con.commit()
