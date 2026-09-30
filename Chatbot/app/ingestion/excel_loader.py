import pandas as pd


def load_excel(file_path: str) -> dict[str, pd.DataFrame]:

    sheets = pd.read_excel(
        file_path,
        sheet_name=None
    )

    return sheets