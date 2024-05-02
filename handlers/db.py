import aiomysql
import json


class DataBase:
    def __init__(self, config_path=None):
        self.config_path = "./config.json" if config_path is None else config_path

    async def connect(self):
        """
        Connects to the database by loading the database configuration from a JSON file located at self.config_path,
        then creates a connection using aiomysql.connect() and creates a cursor using conn.cursor().

        :return: None
        """
        with open(self.config_path) as f:
            config = json.load(f)["database"]
        self.conn = await aiomysql.connect(
            **config, cursorclass=aiomysql.cursors.DictCursor
        )
        self.cursor = await self.conn.cursor()

    async def execute_query(self, query, args=None):
        """
        Execute a database query.

        :param query: str, SQL query to execute
        :param args: list or tuple, optional parameters to pass to the query
        :return: result of fetchall() method for the executed query
        """
        await self.cursor.execute(query, args)
        await self.conn.commit()
        return await self.cursor.fetchall()

    async def create(self, table, columns, values):
        """
        Creates a new record in the specified table.

        :param table: str, name of the table to insert into
        :param columns: list of str, names of the columns to insert into
        :param values: list of values, values to insert into the columns
        :return: bool, True if the record was created, False if it already exists 
        """
        column_names = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        where = f"{columns[0]}='{values[0]}'"
        query = f"SELECT * FROM {table} WHERE {where}"
        result = await self.execute_query(query)
        if result:
            return False
        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
        await self.execute_query(query, values)
        return True

    async def insert(self, table, columns, values):
        """
        Inserts data into the specified table.

        :param table: str, name of the table to insert into
        :param columns: list of str, names of the columns to insert into
        :param values: list of values, values to insert into the columns
        """
        column_names = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
        await self.execute_query(query, values)

    async def read(self, table, columns=None, where=None):
        """
        Reads data from the specified table.

        :param table: str, name of the table to read from
        :param columns: list of str (optional), names of the columns to read. If None, all columns will be read.
        :param where: str (optional), a condition for the data to be selected. If None, all data will be selected.
        :return: list of tuples, the fetched data
        """
        column_names = ", ".join(columns) if columns else "*"
        query = f"SELECT {column_names} FROM {table}"
        if where:
            query += f" WHERE {where}"
        return await self.execute_query(query)

    async def update(self, table, set_columns, set_values, where=None):
        """
        Updates data in the specified table

        :param table: str, name of the table to update
        :param set_columns: list of str, names of the columns to be updated
        :param set_values: list of values, corresponding to the columns in set_columns
        :param where: str (optional), a condition for the data to be updated. If None, all data will be updated.
        """
        set_statements = ", ".join([f"{col}=%s" for col in set_columns])
        query = f"UPDATE {table} SET {set_statements}"
        if where:
            query += f" WHERE {where}"
        await self.execute_query(query, set_values)

    async def delete(self, table, where=None):
        """
        Deletes data from the specified table.

        :param table: str, name of the table to delete from
        :param where: str (optional), a condition for the data to be deleted. If None, all data will be deleted.
        """
        query = f"DELETE FROM {table}"
        if where:
            query += f" WHERE {where}"
        await self.execute_query(query)

    async def increment(self, table, column, value, where=None):
        """
        Increments a certain column in the database.

        :param table: str, name of the table to update
        :param column: str, name of the column to increment
        :param where: str (optional), a condition for the data to be updated. If None, all data will be updated.
        """
        query = f"UPDATE {table} SET {column} = {column} + {value}"
        if where:
            query += f" WHERE {where}"
        await self.execute_query(query)

    async def decrement(self, table, column, value, where=None):
        """
        Decrements a certain column in the database.

        :param table: str, name of the table to update
        :param column: str, name of the column to decrement
        :param where: str (optional), a condition for the data to be updated. If None, all data will be updated.
        """
        query = f"UPDATE {table} SET {column} = {column} - {value}"
        if where:
            query += f" WHERE {where}"
        await self.execute_query(query)

    async def __aenter__(self):
        """
        Connects to the database.
        This method is used as a context manager and should be used in "async with" statement.
        """
        await self.connect()
        return self

    async def __aexit__(self, *args):
        """
        Closes the database connection.
        This method is automatically called when used as a context manager.
        """
        self.conn.close()
