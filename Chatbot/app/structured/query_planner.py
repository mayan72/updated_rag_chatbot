import re

from app.utils.logger import logger


class StructuredQueryPlanner:

    def __init__(self, structured_db):
        self.structured_db = structured_db

    def plan(self, question: str, table_name: str):

        logger.info("========== STRUCTURED PLANNING START ==========")
        logger.info("Question: %s", question)
        logger.info("Table: %s", table_name)

        columns = self.structured_db.get_columns(table_name)

        logger.info("Available columns: %s", columns)

        operation = self._detect_operation(question)

        logger.info("Detected operation: %s", operation)

        # COUNT does not need a target column.
        if operation == "count":

            logger.info(
                "Operation is COUNT. Target column is not required."
            )

            target_column = None

        else:

            logger.info(
                "Operation is %s. Detecting target column.",
                operation,
            )

            target_column = self._detect_target_column(
                question=question,
                columns=columns,
                operation=operation,
            )

        logger.info(
            "Detected target column: %s",
            target_column,
        )

        filters = self._detect_filters(
            question=question,
            table_name=table_name,
            columns=columns,
        )

        logger.info(
            "Detected filters: %s",
            filters,
        )

        plan = {
            "table_name": table_name,
            "operation": operation,
            "target_column": target_column,
            "filters": filters,
        }

        logger.info("Final structured plan: %s", plan)
        logger.info("========== STRUCTURED PLANNING END ==========")

        return plan

    def _detect_operation(self, question: str):

        question_lower = question.lower().strip()

        logger.debug(
            "Detecting operation from question: %s",
            question,
        )

        count_patterns = [
            r"\bhow many\b",
            r"\bnumber of\b",
            r"\bcount\b",
            r"\bcount of\b",
        ]

        for pattern in count_patterns:

            if re.search(pattern, question_lower):

                logger.debug(
                    "COUNT matched pattern: %s",
                    pattern,
                )

                return "count"

        max_patterns = [
            r"\bmaximum\b",
            r"\bmax\b",
            r"\bhighest\b",
            r"\blargest\b",
        ]

        for pattern in max_patterns:

            if re.search(pattern, question_lower):

                logger.debug(
                    "MAX matched pattern: %s",
                    pattern,
                )

                return "max"

        min_patterns = [
            r"\bminimum\b",
            r"\bmin\b",
            r"\blowest\b",
            r"\bsmallest\b",
        ]

        for pattern in min_patterns:

            if re.search(pattern, question_lower):

                logger.debug(
                    "MIN matched pattern: %s",
                    pattern,
                )

                return "min"

        avg_patterns = [
            r"\baverage\b",
            r"\bavg\b",
            r"\bmean\b",
        ]

        for pattern in avg_patterns:

            if re.search(pattern, question_lower):

                logger.debug(
                    "AVG matched pattern: %s",
                    pattern,
                )

                return "avg"

        sum_patterns = [
            r"\btotal\b",
            r"\bsum\b",
            r"\bcombined\b",
            r"\baltogether\b",
        ]

        for pattern in sum_patterns:

            if re.search(pattern, question_lower):

                logger.debug(
                    "SUM matched pattern: %s",
                    pattern,
                )

                return "sum"

        logger.warning(
            "Could not determine operation from question: %s",
            question,
        )

        raise ValueError(
            f"Could not determine operation from question: {question!r}"
        )

    def _detect_target_column(
        self,
        question,
        columns,
        operation,
    ):

        logger.debug(
            "Detecting target column. Operation=%s Columns=%s",
            operation,
            columns,
        )

        question_lower = question.lower()

        def normalize(value):
            return re.sub(
                r"[^a-z0-9]",
                "",
                str(value).lower(),
            )

        normalized_question = normalize(question)

        # Exact column name
        for column in columns:

            if str(column).lower() in question_lower:

                logger.debug(
                    "Target column matched exactly: %s",
                    column,
                )

                return column

        # Normalized column name
        for column in columns:

            normalized_column = normalize(column)

            if (
                normalized_column
                and normalized_column in normalized_question
            ):

                logger.debug(
                    "Target column matched after normalization: %s",
                    column,
                )

                return column

        semantic_aliases = {
            "sales": [
                "sales",
                "sale",
                "revenue",
                "amount",
            ],
            "quantity": [
                "quantity",
                "qty",
                "units",
            ],
            "unit_price": [
                "unit price",
                "price",
                "unitprice",
            ],
        }

        for column in columns:

            aliases = semantic_aliases.get(
                normalize(column),
                [],
            )

            for alias in aliases:

                if alias in question_lower:

                    logger.debug(
                        "Target column matched semantic alias '%s' -> %s",
                        alias,
                        column,
                    )

                    return column

        logger.error(
            "TARGET COLUMN NOT FOUND | question=%r | operation=%s | columns=%s",
            question,
            operation,
            columns,
        )

        raise ValueError(
            f"Could not safely determine the target column "
            f"from question: {question!r}. "
            f"Available columns: {columns}"
        )

    def _detect_filters(
        self,
        question,
        table_name,
        columns,
    ):

        logger.debug(
            "Detecting filters for question: %s",
            question,
        )

        filters = {}

        question_lower = question.lower()

        for column in columns:

            values = self.structured_db.get_distinct_values(
                table_name,
                column,
            )

            logger.debug(
                "Column '%s' distinct values: %s",
                column,
                values,
            )

            for value in values:

                if value is None:
                    continue

                value_text = str(value).strip()

                if not value_text:
                    continue

                if value_text.lower() in question_lower:

                    logger.info(
                        "Filter detected: %s = %s",
                        column,
                        value,
                    )

                    filters[column] = value

        return filters