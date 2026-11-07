import pandas as pd
import os


INPUT_FILE = "data/school_directory.csv"

OUTPUT_FILE = "data/school_coordinates.csv"

MISSING_FILE = "data/schools_needing_coordinates.csv"


if not os.path.exists(INPUT_FILE):

    raise FileNotFoundError(
        "school_directory.csv was not found. "
        "Run Script 1 first."
    )

schools = pd.read_csv(INPUT_FILE)

# Ensure coordinate columns exist
for column in ["latitude", "longitude"]:

    if column not in schools.columns:
        schools[column] = None

# Convert coordinates to numeric values
schools["latitude"] = pd.to_numeric(
    schools["latitude"],
    errors="coerce"
)

schools["longitude"] = pd.to_numeric(
    schools["longitude"],
    errors="coerce"
)


valid_coordinates = (
    schools["latitude"].between(-90, 90)
    &
    schools["longitude"].between(-180, 180)
)


schools.loc[
    ~valid_coordinates,
    ["latitude", "longitude"]
] = None


schools["coordinate_status"] = "missing_coordinates"

schools.loc[
    valid_coordinates,
    "coordinate_status"
] = "coordinates_available"


schools_with_coordinates = schools[
    schools["coordinate_status"] == "coordinates_available"
].copy()

schools_without_coordinates = schools[
    schools["coordinate_status"] == "missing_coordinates"
].copy()


os.makedirs("data", exist_ok=True)

schools.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

schools_without_coordinates.to_csv(
    MISSING_FILE,
    index=False,
    encoding="utf-8-sig"
)


total = len(schools)

found = len(schools_with_coordinates)

missing = len(schools_without_coordinates)

percentage = (found / total * 100) if total > 0 else 0

print("\n===================================")
print("COORDINATE CHECK COMPLETE")
print("===================================")

print(f"Total schools: {total}")
print(f"Coordinates available: {found}")
print(f"Coordinates missing: {missing}")

print(f"Coverage: {percentage:.2f}%")

print("\nExported files:")
print(OUTPUT_FILE)
print(MISSING_FILE)

if missing > 0:

    print(
        "\nSome schools still need coordinates. "
        "See schools_needing_coordinates.csv."
    )

else:
    print("\nAll schools have coordinates!")
