import configparser
from random import randint

import mysql.connector


class Mysql:
    def __init__(self, db="edith", user="E.D.I.T.H"):
        config = configparser.ConfigParser()
        config.read('config.ini')
        pwd = config["DEFAULT"]["mysql_password"]

        self.__db = db

        self.__connection = mysql.connector.connect(
            host="localhost",
            user=user,
            passwd=pwd,
            db=db,
            auth_plugin="mysql_native_password"
        )

        self.__connection.set_charset_collation("utf8mb4", "utf8mb4_unicode_ci")

        self.__cursor = self.__connection.cursor(buffered=True, dictionary=True)

    def get_uuid(self, table, colm, length=8):
        def get_uuid():
            characters = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            characters_length = len(characters)
            uuid_ = ''
            i = 0
            while i < length:
                uuid_ += characters[randint(0, characters_length - 1)]
                i += 1
            return uuid_

        while True:
            uuid = get_uuid()
            existing_uuids = self.select(table=table, colms=colm, clause=f"WHERE {colm}='{uuid}'")
            if len(existing_uuids) == 0:
                return uuid

    def get_cursor(self):
        return self.__cursor

    def does_table_exist(self, searched_table):
        tables = []

        self.__cursor.execute("SHOW TABLES")

        for table in self.__cursor:
            if type(table[f"Tables_in_{self.__db}"]) is bytearray:
                tables.append(table[f"Tables_in_{self.__db}"].decode())
            elif type(table[f"Tables_in_{self.__db}"]) is str:
                tables.append(table[f"Tables_in_{self.__db}"])

        if searched_table.lower() in tables:
            return True
        else:
            return False

    def insert(self, table, colms, values, commit=True):
        if self.does_table_exist(table):
            self.__cursor.execute(
                "INSERT INTO {} {} VALUES (".format(table, colms) + ("%s," * (len(values)))[:-1] + ")", values
            )

            if commit:
                self.commit()

    def select(self, table, colms, clause=""):
        self.commit()
        re = None
        self.__cursor.execute(f"SELECT {colms} from {table} {clause}")
        re = self.__cursor.fetchall()
        return re

    def delete(self, table, clause, limit="", commit=True):
        self.__cursor.execute(f"SELECT EXISTS(SELECT * from {table} {clause})")

        if self.__cursor.fetchall()[0][f"EXISTS(SELECT * from {table} {clause})"]:
            self.__cursor.execute(f"DELETE FROM {table} {clause} {limit}")

        if commit:
            self.commit()

    def create_table(self, table, colms):
        if not self.does_table_exist(table):
            self.__cursor.execute(f"CREATE TABLE {table} {colms}")

    def drop_table(self, table):
        if self.does_table_exist(table):
            self.__cursor.execute(f"DROP TABLE {table}")

    def add_colm(self, table, colm, definition, clause):
        if self.does_table_exist(table) and not self.column_exist(table=table, colm=colm):
            self.__cursor.execute(f"ALTER TABLE {table} ADD {colm} {definition} {clause}")

    def search(self, table, clause=""):
        re = None
        if self.does_table_exist(table):
            self.__cursor.execute(f"SELECT EXISTS(SELECT * from {table} {clause})")

            re = self.__cursor.fetchall()[0][f"EXISTS(SELECT * from {table} {clause})"]
        return re

    def update(self, table, value, clause="", commit=True):
        if self.does_table_exist(table):
            self.__cursor.execute(f"SELECT EXISTS(SELECT * from {table} {clause})")

            if self.__cursor.fetchall()[0][f"EXISTS(SELECT * from {table} {clause})"]:
                self.__cursor.execute(f"UPDATE {table} SET {value} {clause}")

            if commit:
                self.commit()

    def close(self):
        self.__cursor.close()

    def commit(self):
        try:
            self.__connection.commit()
        except Exception as e:
            print(e)

    def column_exist(self, table, colm):
        self.__cursor.execute(f"show columns from {table} like '{colm}'")
        re = self.__cursor.fetchall()
        if len(re) == 0:
            return False
        else:
            return True

    def execute(self, sql, multi=False, commit=True):
        if commit:
            self.commit()

        result = self.__cursor.execute(sql, multi=multi)

        if commit:
            self.commit()

        return result
