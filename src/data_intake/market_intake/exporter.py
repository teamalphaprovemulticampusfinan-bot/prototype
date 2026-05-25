from __future__ import annotations

import pandas as pd

from .config import OUTPUT_DIR, CSV_FILENAME, CSV_ENCODING


def save_csv(rows: list[dict], filename: str | None = None):
    filename = filename or CSV_FILENAME

    df = pd.DataFrame(rows)
    output_path = OUTPUT_DIR / filename

    df.to_csv(output_path, index=False, encoding=CSV_ENCODING)

    return output_path