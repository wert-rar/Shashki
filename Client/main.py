import pymysql
from config import host, user, password, db_name


try:
    connection = pymysql.connect(
        host=host,
        port=3306,
        user=user,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )
    print("successfully connected...")
except Exception as ex:
    print("Connection refused...")
    print(ex)
