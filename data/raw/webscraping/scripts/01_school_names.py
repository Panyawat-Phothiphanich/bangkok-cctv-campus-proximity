
import pandas as pd
import os
import re
import unicodedata

RAW_FOLDER = "raw_data"
OUTPUT_FOLDER = "data"

SOURCES = [
    {
        "file": "bma_schools.xlsx",
        "organization": "Bangkok Metropolitan Administration",
        "school_type": "BMA public school"
    },
    {
        "file": "obec_schools.csv",
        "organization": "Office of the Basic Education Commission",
        "school_type": "OBEC school"
    },
    {
        "file": "opec_schools.csv",
        "organization": "Office of the Private Education Commission",
        "school_type": "Private school"
    }
]


ALIASES = {
    "school_name": [
        "school_name",
        "name",
        "school",
        "ชื่อโรงเรียน"
    ],

    "school_id": [
        "school_id",
        "school_code",
        "id_sch",
        "รหัสโรงเรียน"
    ],

    "address": [
        "address",
        "ที่อยู่"
    ],

    "district": [
        "district",
        "district_name",
        "amphoe",
        "อำเภอ",
        "เขต"
    ],

    "subdistrict": [
        "subdistrict",
        "sub_district",
        "tambon",
        "ตำบล",
        "แขวง"
    ],

    "latitude": [
        "latitude",
        "lat",
        "ละติจูด"
    ],

    "longitude": [
        "longitude",
        "lon",
        "lng",
        "ลองจิจูด"
    ],

    "postal_code": [
        "postal_code",
        "postcode",
        "zip_code",
        "รหัสไปรษณีย์"
    ]
}


def normalize_column(column):

    column = str(column).strip().lower()
    column = unicodedata.normalize("NFKC", column)

    return re.sub(r"[\s_\-]+", "", column)


def find_column(df, possible_names):

    normalized_columns = {
        normalize_column(column): column
        for column in df.columns
    }

    for name in possible_names:

        key = normalize_column(name)

        if key in normalized_columns:
            return normalized_columns[key]

    return None


def read_source_file(path):

    extension = os.path.splitext(path)[1].lower()

    if extension in [".xlsx", ".xls"]:
        return pd.read_excel(
            path,
            dtype=str
        )

    if extension == ".csv":

        for encoding in ["utf-8-sig", "cp874", "utf-8"]:

            try:
                return pd.read_csv(
                    path,
                    dtype=str,
                    encoding="utf-8-sig"
                )

            except UnicodeDecodeError:
                continue

        raise ValueError("Unable to identify CSV encoding.")

    raise ValueError(f"Unsupported file type: {extension}")


def clean_value(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value.lower() in ["", "nan", "none", "null"]:
        return None

    return value


def extract_column(df, field):

    column = find_column(df, ALIASES[field])

    if column is None:
        return pd.Series([None] * len(df), index=df.index)

    return df[column].apply(clean_value)


def normalize_school_data(df, source):

    school_names = extract_column(df, "school_name")

    result = pd.DataFrame({
        "school_name": school_names,
        "school_id": extract_column(df, "school_id"),
        "district": extract_column(df, "district"),
        "subdistrict": extract_column(df, "subdistrict"),
        "address": extract_column(df, "address"),
        "latitude": extract_column(df, "latitude"),
        "longitude": extract_column(df, "longitude"),
        "postal_code": extract_column(df, "postal_code")
    })

    result = result.dropna(subset=["school_name"])

    result = result[
        ~result["school_name"].str.upper().isin(
            ["SCHOOLNAME", "NAME", "ชื่อสถานศึกษา"]
        )
    ]

    result["organization"] = source["organization"]
    result["school_type"] = source["school_type"]
    result["source_file"] = source["file"]

    return result


# --------------------------------------------------
# THE MAIN PART
# --------------------------------------------------

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

all_schools = []

for source in SOURCES:

    file_path = os.path.join(
        RAW_FOLDER,
        source["file"]
    )

    if not os.path.exists(file_path):

        print(f"Source file not found: {source['file']}")
        continue

    print(f"\nReading: {source['file']}")

    try:

        raw_data = read_source_file(file_path)

        print("Available columns:")
        print(list(raw_data.columns))

        cleaned_data = normalize_school_data(
            raw_data,
            source
        )

        print(f"Schools extracted: {len(cleaned_data)}")

        all_schools.append(cleaned_data)

    except Exception as error:

        print(f"Could not process {source['file']}: {error}")


if not all_schools:

    raise ValueError(
        "No school data was collected. "
        "Check your downloaded files and column names."
    )


schools = pd.concat(
    all_schools,
    ignore_index=True
)


for column in ["latitude", "longitude"]:

    schools[column] = pd.to_numeric(
        schools[column],
        errors="coerce"
    )


invalid_coordinates = (
    (schools["latitude"].notna() &
     ~schools["latitude"].between(-90, 90))
    |
    (schools["longitude"].notna() &
     ~schools["longitude"].between(-180, 180))
)

schools.loc[
    invalid_coordinates,
    ["latitude", "longitude"]
] = None


schools["dedup_key"] = (
    schools["school_name"].fillna("").str.strip().str.lower()
    + "|"
    + schools["district"].fillna("").str.strip().str.lower()
    + "|"
    + schools["address"].fillna("").str.strip().str.lower()
)


schools = schools.drop_duplicates(
    subset=["dedup_key"]
)


schools = schools.drop(columns=["dedup_key"])


schools = schools.reset_index(drop=True)


schools.to_csv(
    os.path.join(OUTPUT_FOLDER, "school_directory.csv"),
    index=False,
    encoding="utf-8-sig"
)


school_names = schools[["school_name"]].drop_duplicates()

school_names.to_csv(
    os.path.join(OUTPUT_FOLDER, "school_names.csv"),
    index=False,
    encoding="utf-8-sig"
)


print("\n===================================")
print("SCHOOL DATABASE CREATED")
print("===================================")

print(f"Total unique records: {len(schools)}")

print("\nRecords by organization:")

print(
    schools["organization"].value_counts()
)

print("\nRecords with coordinates:")

print(
    schools[["latitude", "longitude"]].notna().all(axis=1).sum()
)

print("\nRecords without coordinates:")

print(
    schools[["latitude", "longitude"]].isna().any(axis=1).sum()
)

print("\nFiles exported:")
print("data/school_directory.csv")
print("data/school_names.csv")
