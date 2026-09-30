import sqlite3
import pandas as pd


class StructuredDatabase:

    def __init__(self, db_path):
        self.db_path = db_path

    def save_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
    ):
        connection = sqlite3.connect(self.db_path)

        try:
            df.to_sql(
                table_name,
                connection,
                if_exists="replace",
                index=False,
            )

            connection.commit()

        finally:
            connection.close()

    def execute(self, query):

        connection = sqlite3.connect(self.db_path)

        try:
            return pd.read_sql_query(
                query,
                connection,
            )

        finally:
            connection.close()

    def get_columns(self, table_name):

        connection = sqlite3.connect(self.db_path)

        try:
            rows = connection.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            return [row[1] for row in rows]

        finally:
            connection.close()

    def get_distinct_values(self, table_name, column):

        connection = sqlite3.connect(self.db_path)

        try:
            rows = connection.execute(
                f'''
                SELECT DISTINCT "{column}"
                FROM "{table_name}"
                WHERE "{column}" IS NOT NULL
                '''
            ).fetchall()

            return [row[0] for row in rows]

        finally:
            connection.close()

    def get_schema_context(self, table_name: str) -> str:
        """
        Dynamically build schema context from the SQLite table.

        This method does not hardcode column names or values.
        """

        connection = sqlite3.connect(self.db_path)

        try:
            rows = connection.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            if not rows:
                raise ValueError(
                    f"Table '{table_name}' does not exist or has no columns."
                )

            lines = [
                f"Table: {table_name}",
                "",
                "Columns:",
            ]

            for row in rows:
                column_name = row[1]
                column_type = row[2] or "UNKNOWN"

                lines.append(
                    f"- {column_name}: {column_type}"
                )

            return "\n".join(lines)

        finally:
            connection.close()