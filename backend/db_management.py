from typing import Tuple, Any, List
import mysql.connector as connector
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from mysql.connector.pooling import PooledMySQLConnection


class DBManager:
    def __init__(self, db_host: str, db_user: str, db_password: str, db_name: str):
        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name

    def connect_to_db(self) -> Tuple[
        PooledMySQLConnection | MySQLConnectionAbstract, MySQLCursorAbstract]:
        try:
            db_connection = connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            db_cursor = db_connection.cursor()
            return db_connection, db_cursor
        except connector.Error as e:
            print(f"Error connecting to MySQL: {e}")

    @staticmethod
    def close_db_connection(db_connection, db_cursor) -> None:
        if db_connection and db_connection.is_connected():
            db_cursor.close()
            db_connection.close()
            print("MySQL connection is closed")
        else:
            print("No active database connection to close.")

    def execute_transaction(self, queries: List[str], values: List[tuple]) -> Any:
        db_connection, db_cursor = self.connect_to_db()
        for i in range(len(queries)):
            db_cursor.execute(queries[i], values[i])
        res = db_cursor.fetchall()
        db_connection.commit()
        self.close_db_connection(db_connection, db_cursor)
        return res
