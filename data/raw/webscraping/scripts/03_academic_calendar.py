from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FOLDER = PROJECT_ROOT / "raw_data" / "calendar_sources"
OUTPUT_FILE = PROJECT_ROOT / "raw_data" / "school_calendar_sources.csv"

REQUIRED_COLUMNS = [
    "school_name",
    "organization",
    "school_type",
    "scope",
    "academic_year",
    "semester",
    "start_date",
    "end_date",
    "source_url",
    "collection_method",
    "confidence"
]


def main():

    if not INPUT_FOLDER.exists():
        print(f"Input folder not found: {INPUT_FOLDER}")
        return

    csv_files = sorted(INPUT_FOLDER.glob("*.csv"))

    if not csv_files:
        print("No CSV files found in calendar_sources.")
        return

    combined = []

    for filepath in csv_files:

        print(f"Reading: {filepath.name}")

        try:
            df = pd.read_csv(
                filepath,
                dtype=str,
                encoding="utf-8-sig"
            )

        except Exception as error:
            print(f"Could not read {filepath.name}: {error}")
            continue

        df.columns = df.columns.str.strip().str.lower()

        missing_columns = [
            column for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            print(
                f"Skipping {filepath.name}. "
                f"Missing columns: {missing_columns}"
            )
            continue

        df = df[REQUIRED_COLUMNS].copy()

        df["input_file"] = filepath.name

        combined.append(df)

    if not combined:
        print("No valid calendar files could be combined.")
        return

    result = pd.concat(combined, ignore_index=True)

    for column in result.columns:
        result[column] = result[column].fillna("").astype(str).str.strip()

    before = len(result)

    result = result.drop_duplicates(
        subset=REQUIRED_COLUMNS
    ).reset_index(drop=True)

    removed = before - len(result)


    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCalendar source combination complete.")
    print(f"Files processed: {len(combined)}")
    print(f"Records collected: {before}")
    print(f"Exact duplicate records removed: {removed}")
    print(f"Final records: {len(result)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
