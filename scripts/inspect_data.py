import pandas as pd
import geopandas as gpd
import os

DATA_FOLDER = "datasets/raw"

print("\n========== DATASET INSPECTION ==========\n")

for file in os.listdir(DATA_FOLDER):

    file_path = os.path.join(DATA_FOLDER, file)

    print("\n" + "=" * 60)
    print("FILE:", file)

    try:

        if file.endswith(".xlsx"):

            excel = pd.ExcelFile(file_path)

            print("Available Sheets:", excel.sheet_names)

            for sheet in excel.sheet_names:

                print("\nSHEET:", sheet)

                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet,
                    nrows=100
                )

                print("Columns:", df.columns.tolist())

                print("\nFirst 5 Records:")
                print(df.head())

                print("\nMissing Values:")
                print(df.isnull().sum())

                print("\nData Types:")
                print(df.dtypes)

        elif file.endswith(".geojson"):

            gdf = gpd.read_file(file_path)

            print("Total Features:", len(gdf))
            print("Columns:", gdf.columns.tolist())
            print("Coordinate System:", gdf.crs)

            print("\nFirst 5 Records:")
            print(gdf.head())

    except Exception as e:

        print("ERROR:", e)

print("\n========== INSPECTION COMPLETED ==========")