import re
import sqlite3
from typing import Any, Optional
from app.utils.logger import logger

class StructuredExecutor:
    """
    Safe executor for structured Excel data stored in SQLite.

    Supported operations:
        - SUM
        - AVG
        - COUNT
        - MIN
        - MAX
        - GROUP BY

    The executor does not accept raw SQL from the user/LLM.
    It builds SQL only from validated identifiers and parameters.
    """

    ALLOWED_AGGREGATIONS = {
        "sum": "SUM",
        "avg": "AVG",
        "average": "AVG",
        "count": "COUNT",
        "min": "MIN",
        "max": "MAX",
    }

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ---------------------------------------------------------
    # Connection
    # ---------------------------------------------------------

    def _connect(self):
        return sqlite3.connect(self.db_path)

    # ---------------------------------------------------------
    # Identifier validation
    # ---------------------------------------------------------

    @staticmethod
    def _validate_identifier(value: str) -> str:
        """
        Validate SQLite table/column identifiers.

        We don't parameterize identifiers with '?' because SQLite
        parameters are for values, not table/column names.
        """

        if not value:
            raise ValueError("Identifier cannot be empty.")

        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
            raise ValueError(
                f"Unsafe SQL identifier: {value}"
            )

        return value

    # ---------------------------------------------------------
    # Table validation
    # ---------------------------------------------------------

    def _table_exists(self, table_name: str) -> bool:

        table_name = self._validate_identifier(table_name)

        connection = self._connect()

        try:
            cursor = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name = ?
                """,
                (table_name,),
            )

            return cursor.fetchone() is not None

        finally:
            connection.close()

    # ---------------------------------------------------------
    # Get columns
    # ---------------------------------------------------------

    def get_columns(self, table_name: str) -> list[str]:

        table_name = self._validate_identifier(table_name)

        if not self._table_exists(table_name):
            raise ValueError(
                f"Table '{table_name}' does not exist."
            )

        connection = self._connect()

        try:
            rows = connection.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            return [row[1] for row in rows]

        finally:
            connection.close()

    # ---------------------------------------------------------
    # Resolve column
    # ---------------------------------------------------------

    def resolve_column(
        self,
        table_name: str,
        requested_column: str,
    ) -> str:

        columns = self.get_columns(table_name)

        requested_normalized = (
            requested_column.strip().lower()
        )

        # Exact match
        for column in columns:

            if column.lower() == requested_normalized:
                return column

        # Normalized match
        def normalize(value: str) -> str:
            return re.sub(
                r"[^a-z0-9]",
                "",
                value.lower(),
            )

        requested_normalized = normalize(
            requested_column
        )

        for column in columns:

            if normalize(column) == requested_normalized:
                return column

        raise ValueError(
            f"Column '{requested_column}' "
            f"not found in table '{table_name}'. "
            f"Available columns: {columns}"
        )

    # ---------------------------------------------------------
    # Resolve aggregation
    # ---------------------------------------------------------

    def resolve_aggregation(
        self,
        operation: str,
    ) -> str:

        operation = operation.strip().lower()

        if operation not in self.ALLOWED_AGGREGATIONS:
            raise ValueError(
                f"Unsupported aggregation: {operation}"
            )

        return self.ALLOWED_AGGREGATIONS[operation]

    # ---------------------------------------------------------
    # Aggregate
    # ---------------------------------------------------------

    def aggregate(
        self,
        table_name: str,
        operation: str,
        target_column: Optional[str],
        filters: Optional[dict[str, Any]] = None,
    ) -> Any:

        table_name = self._validate_identifier(
            table_name
        )

        if not self._table_exists(table_name):
            raise ValueError(
                f"Table '{table_name}' does not exist."
            )

        logger.info(
            "Structured execution started | table=%s | operation=%s | target_column=%s | filters=%s",
            table_name,
            operation,
            target_column,
            filters,
        )

        operation = operation.strip().lower()

        # COUNT is a row-level operation.
        # It does not require a target column.
        if operation == "count":

            logger.info(
                "COUNT operation detected. Using count_rows() instead of aggregate column resolution."
            )

            result = self.count_rows(
                table_name=table_name,
                filters=filters,
            )

            logger.info(
                "Structured COUNT result | table=%s | filters=%s | result=%s",
                table_name,
                filters,
                result,
            )

            return result

        # All other aggregations require a target column.
        if not target_column:
            raise ValueError(
                f"Target column is required for operation '{operation}'."
            )

        target_column = self.resolve_column(
            table_name,
            target_column,
        )

        logger.info(
            "Resolved target column: %s",
            target_column,
        )

        aggregation = self.resolve_aggregation(
            operation
        )

        filters = filters or {}

        where_clauses = []
        parameters = []

        available_columns = self.get_columns(
            table_name
        )

        normalized_columns = {
            column.lower(): column
            for column in available_columns
        }

        for filter_column, filter_value in filters.items():

            actual_column = normalized_columns.get(
                filter_column.lower()
            )

            if actual_column is None:
                raise ValueError(
                    f"Filter column '{filter_column}' "
                    f"does not exist."
                )

            where_clauses.append(
                f'"{actual_column}" = ?'
            )

            parameters.append(filter_value)

        sql = (
            f'SELECT {aggregation}("{target_column}") '
            f'FROM "{table_name}"'
        )

        if where_clauses:

            sql += (
                " WHERE "
                + " AND ".join(where_clauses)
            )

        connection = self._connect()

        try:
            logger.debug(
                "COUNT SQL: %s",
                sql,
            )

            logger.debug(
                "COUNT PARAMETERS: %s",
                parameters,
            )

            cursor = connection.execute(
                sql,
                parameters,
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return row[0]

        finally:
            connection.close()

    # ---------------------------------------------------------
    # Count rows
    # ---------------------------------------------------------

    def count_rows(
    self,
    table_name: str,
    filters: Optional[dict[str, Any]] = None,
) -> int:

        logger.info(
            "COUNT ROWS | table=%s | filters=%s",
            table_name,
            filters,
        )

        table_name = self._validate_identifier(
            table_name
        )

        if not self._table_exists(table_name):
            raise ValueError(
                f"Table '{table_name}' does not exist."
            )

        filters = filters or {}

        where_clauses = []
        parameters = []

        available_columns = self.get_columns(
            table_name
        )

        normalized_columns = {
            column.lower(): column
            for column in available_columns
        }

        for filter_column, filter_value in filters.items():

            actual_column = normalized_columns.get(
                filter_column.lower()
            )

            if actual_column is None:
                raise ValueError(
                    f"Filter column '{filter_column}' "
                    f"does not exist."
                )

            where_clauses.append(
                f'"{actual_column}" = ?'
            )

            parameters.append(filter_value)

        sql = (
            f'SELECT COUNT(*) '
            f'FROM "{table_name}"'
        )

        if where_clauses:

            sql += (
                " WHERE "
                + " AND ".join(where_clauses)
            )

        connection = self._connect()

        try:

            cursor = connection.execute(
                sql,
                parameters,
            )

            return cursor.fetchone()[0]

        finally:
            connection.close()

    # ---------------------------------------------------------
    # Group by
    # ---------------------------------------------------------

    def group_by(
        self,
        table_name: str,
        group_column: str,
        operation: str,
        target_column: str,
        filters: Optional[dict[str, Any]] = None,
    ):

        table_name = self._validate_identifier(
            table_name
        )

        if not self._table_exists(table_name):
            raise ValueError(
                f"Table '{table_name}' does not exist."
            )

        group_column = self.resolve_column(
            table_name,
            group_column,
        )

        target_column = self.resolve_column(
            table_name,
            target_column,
        )

        aggregation = self.resolve_aggregation(
            operation
        )

        filters = filters or {}

        where_clauses = []
        parameters = []

        available_columns = self.get_columns(
            table_name
        )

        normalized_columns = {
            column.lower(): column
            for column in available_columns
        }

        for filter_column, filter_value in filters.items():

            actual_column = normalized_columns.get(
                filter_column.lower()
            )

            if actual_column is None:
                raise ValueError(
                    f"Filter column '{filter_column}' "
                    f"does not exist."
                )

            where_clauses.append(
                f'"{actual_column}" = ?'
            )

            parameters.append(filter_value)

        sql = f"""
            SELECT
                "{group_column}",
                {aggregation}("{target_column}") AS result
            FROM "{table_name}"
        """

        if where_clauses:

            sql += (
                " WHERE "
                + " AND ".join(where_clauses)
            )

        sql += f'''
            GROUP BY "{group_column}"
            ORDER BY result DESC
        '''

        connection = self._connect()

        try:

            cursor = connection.execute(
                sql,
                parameters,
            )

            rows = cursor.fetchall()

            return [
                {
                    "group": row[0],
                    "value": row[1],
                }
                for row in rows
            ]

        finally:
            connection.close()