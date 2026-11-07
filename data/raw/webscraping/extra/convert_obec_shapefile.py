# --------------------------------------------------
# File for converting obec_schools into a csv, because the website decided to give me the shapefile instead
# --------------------------------------------------
import geopandas as gpd

shapefile_path = "raw_data/obec_schools/bec_school.shp"
schools = gpd.read_file(shapefile_path)

print("Original CRS:", schools.crs)

if schools.crs is None:
    raise ValueError(
        "No coordinate reference system found. "
        "Check that bec_school.prj is present."
    )

schools = schools.to_crs(epsg=4326)

points = schools.geometry.representative_point()

schools["longitude"] = points.x
schools["latitude"] = points.y

schools = schools.drop(columns=["geometry"])

schools.to_csv(
    "raw_data/obec_schools.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nConversion complete!")
print("Number of schools:", len(schools))
print("\nAvailable columns:")
print(schools.columns.tolist())

print("\nFirst five records:")
print(schools.head())