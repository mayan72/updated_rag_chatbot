import pandas as pd


def detect_sheet_type(df: pd.DataFrame) -> str:

    if df.empty:
        return "empty"

    numeric_columns = df.select_dtypes(
        include="number"
    ).shape[1]

    total_columns = len(df.columns)

    if total_columns == 0:
        return "empty"

    numeric_ratio = numeric_columns / total_columns

    if numeric_ratio >= 0.3:
        return "structured"

    return "unstructured"