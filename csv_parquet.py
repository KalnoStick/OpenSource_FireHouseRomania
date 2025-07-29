import os
import pandas as pd

CSV_FOLDER = 'csv_chunks'
PARQUET_OUTPUT = 'csv_support/fire_data.parquet'

def convert_csvs_to_parquet(csv_folder, output_parquet):
    all_chunks = []
    for file in os.listdir(csv_folder):
        if file.endswith('.csv'):
            csv_path = os.path.join(csv_folder, file)
            print(f"Processing {csv_path}")
            df = pd.read_csv(csv_path, encoding='utf-8')
            df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
            df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
            df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)
            all_chunks.append(df)

    if all_chunks:
        full_df = pd.concat(all_chunks, ignore_index=True)
        os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
        full_df.to_parquet(output_parquet, index=False)
        print(f"Saved combined data to {output_parquet}")
    else:
        print(" No CSV files found or all were invalid.")

if __name__ == '__main__':
    convert_csvs_to_parquet(CSV_FOLDER, PARQUET_OUTPUT)
