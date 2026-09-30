from typing import Optional

from app.models.query_plan import QueryUnderstanding
from app.structured.database import StructuredDatabase
from app.utils.logger import logger


class QueryPlanValidator:

    ALLOWED_OPERATIONS = {
        "sum",
        "avg",
        "count",
        "min",
        "max",
    }

    ALLOWED_OPERATORS = {
        "=",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
    }

    def __init__(self, structured_db: StructuredDatabase):
        self.db = structured_db

    def validate(
        self,
        understanding: QueryUnderstanding,
        table_name: str,
    ) -> QueryUnderstanding:

        logger.info(
            "Query plan validation started | table=%s | intent=%s",
            table_name,
            understanding.intent,
        )

        # ---------------------------------------------------------
        # Non-structured queries do not require structured validation
        # ---------------------------------------------------------

        if understanding.intent in {
            "unstructured",
            "unknown",
        }:
            logger.info(
                "Structured validation skipped | intent=%s",
                understanding.intent,
            )

            return understanding

        # ---------------------------------------------------------
        # Structured / hybrid query must have a structured plan
        # ---------------------------------------------------------

        plan = understanding.structured_plan

        if plan is None:
            raise ValueError(
                "Structured or hybrid intent requires structured_plan."
            )

        # ---------------------------------------------------------
        # Get actual schema from SQLite
        # ---------------------------------------------------------

        actual_columns = self.db.get_columns(table_name)

        if not actual_columns:
            raise ValueError(
                f"No columns found for table '{table_name}'."
            )

        # Case-insensitive lookup while preserving actual DB names
        column_lookup = {
            column.lower(): column
            for column in actual_columns
        }

        logger.debug(
            "Actual database columns | %s",
            actual_columns,
        )

        # ---------------------------------------------------------
        # Validate operation
        # ---------------------------------------------------------

        operation = plan.operation.lower().strip()

        if operation not in self.ALLOWED_OPERATIONS:
            raise ValueError(
                f"Unsupported operation: '{operation}'."
            )

        # ---------------------------------------------------------
        # Validate target column
        # ---------------------------------------------------------

        if operation == "count":

            # COUNT does not require a target column
            plan.target_column = None

        else:

            if not plan.target_column:
                raise ValueError(
                    f"Target column is required for '{operation}'."
                )

            target_key = plan.target_column.strip().lower()

            if target_key not in column_lookup:
                raise ValueError(
                    f"Invalid target column '{plan.target_column}'. "
                    f"Available columns: {actual_columns}"
                )

            # Replace LLM representation with actual DB column name
            plan.target_column = column_lookup[target_key]

        # ---------------------------------------------------------
        # Validate filters
        # ---------------------------------------------------------

        validated_filters = []

        for filter_item in plan.filters:

            filter_column = filter_item.column.strip()
            filter_key = filter_column.lower()

            if filter_key not in column_lookup:
                raise ValueError(
                    f"Invalid filter column '{filter_column}'. "
                    f"Available columns: {actual_columns}"
                )

            operator = filter_item.operator.strip()

            if operator not in self.ALLOWED_OPERATORS:
                raise ValueError(
                    f"Unsupported filter operator '{operator}'."
                )

            actual_column = column_lookup[filter_key]

            # Validate value against actual DB values for equality filters
            if operator == "=":

                actual_values = self.db.get_distinct_values(
                    table_name=table_name,
                    column=actual_column,
                )

                requested_value = str(
                    filter_item.value
                ).strip()

                matched_value = self._resolve_value(
                    requested_value,
                    actual_values,
                )

                if matched_value is None:
                    raise ValueError(
                        f"Value '{requested_value}' was not found "
                        f"for column '{actual_column}'."
                    )

                filter_item.value = matched_value

            filter_item.column = actual_column

            validated_filters.append(filter_item)

        plan.filters = validated_filters

        # ---------------------------------------------------------
        # Validate GROUP BY
        # ---------------------------------------------------------

        validated_group_by = []

        for group_column in plan.group_by:

            group_key = group_column.strip().lower()

            if group_key not in column_lookup:
                raise ValueError(
                    f"Invalid group_by column '{group_column}'. "
                    f"Available columns: {actual_columns}"
                )

            validated_group_by.append(
                column_lookup[group_key]
            )

        plan.group_by = validated_group_by

        # ---------------------------------------------------------
        # Final logging
        # ---------------------------------------------------------

        logger.info(
            "Query plan validation successful | plan=%s",
            plan.model_dump(),
        )

        return understanding

    @staticmethod
    def _resolve_value(
        requested_value: str,
        actual_values: list,
    ) -> Optional[str]:

        requested_normalized = requested_value.casefold()

        # Exact case-insensitive match
        for actual_value in actual_values:

            if str(actual_value).strip().casefold() == requested_normalized:
                return actual_value

        return None