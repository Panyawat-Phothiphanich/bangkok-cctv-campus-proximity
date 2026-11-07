import pandas as pd

df = pd.read_csv(
    "raw_data/obec_schools.csv",
    dtype=str,
    encoding="utf-8-sig"
)

print("\nCOLUMN NAMES:")
for column in df.columns:
    print(f"- {column}")

print("\nFIRST 10 RECORDS:")
print(df.head(10).to_string())

print("\nNON-EMPTY VALUE COUNTS:")
print(df.notna().sum().to_string())