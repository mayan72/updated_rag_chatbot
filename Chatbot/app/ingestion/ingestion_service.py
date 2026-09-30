import os
import uuid
import pandas as pd


class IngestionService:

    def __init__(
        self,
        embedder,
        vector_store,
        structured_db,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.structured_db = structured_db

    def ingest(self, file_path: str):

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Excel file not found: {file_path}"
            )

        sheets = pd.read_excel(
            file_path,
            sheet_name=None,
        )

        result = {}

        for sheet_name, df in sheets.items():

            if df.empty:
                continue

            sheet_type = self.detect_sheet_type(df)

            # -----------------------------
            # STRUCTURED
            # -----------------------------
            if sheet_type == "structured":

                table_name = self.make_table_name(
                    sheet_name
                )

                self.structured_db.save_dataframe(
                    df=df,
                    table_name=table_name,
                )

                result[sheet_name] = {
                    "type": "structured",
                    "table": table_name,
                    "rows": len(df),
                    "columns": list(df.columns),
                }

            # -----------------------------
            # UNSTRUCTURED
            # -----------------------------
            else:

                documents = []

                for row_number, (_, row) in enumerate(
                    df.iterrows(),
                    start=2,
                ):

                    parts = []

                    for column in df.columns:

                        value = row[column]

                        if pd.notna(value):

                            parts.append(
                                f"{column}: {value}"
                            )

                    text = " | ".join(parts)

                    if text.strip():

                        documents.append(
                            {
                                "text": text,
                                "metadata": {
                                    "file_name": os.path.basename(
                                        file_path
                                    ),
                                    "sheet_name": sheet_name,
                                    "sheet_type": "unstructured",
                                    "row_number": row_number,
                                },
                            }
                        )

                if documents:

                    texts = [
                        item["text"]
                        for item in documents
                    ]

                    embeddings = (
                        self.embedder.embed_documents(
                            texts
                        )
                    )

                    ids = [
                        str(uuid.uuid4())
                        for _ in documents
                    ]

                    metadatas = [
                        item["metadata"]
                        for item in documents
                    ]

                    self.vector_store.add_documents(
                        documents=texts,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        ids=ids,
                    )

                result[sheet_name] = {
                    "type": "unstructured",
                    "documents": len(documents),
                }

        return result

    @staticmethod
    def detect_sheet_type(
        df: pd.DataFrame
    ) -> str:

        if df.empty:
            return "empty"

        numeric_columns = len(
            df.select_dtypes(
                include="number"
            ).columns
        )

        total_columns = len(df.columns)

        if total_columns == 0:
            return "empty"

        numeric_ratio = (
            numeric_columns / total_columns
        )

        if numeric_ratio >= 0.3:
            return "structured"

        return "unstructured"

    @staticmethod
    def make_table_name(
        sheet_name: str
    ) -> str:

        table_name = (
            sheet_name
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        return table_name