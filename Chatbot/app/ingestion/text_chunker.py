def dataframe_to_text(df):

    texts = []

    for _, row in df.iterrows():

        parts = []

        for column in df.columns:

            value = row[column]

            if value is not None:
                parts.append(
                    f"{column}: {value}"
                )

        texts.append(
            " | ".join(parts)
        )

    return texts