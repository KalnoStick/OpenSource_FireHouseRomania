import os
import pandas as pd
import random

csv_folder = "csv_chunks"
output_parquet = "csv_support/Final_sheet.parquet"

chunk_size = 2_000_000  # 2 million rows per batch
sample_size = 500       # Rows to sample per batch

all_samples = []

for file in os.listdir(csv_folder):
    if file.endswith(".csv"):
        file_path = os.path.join(csv_folder, file)
        print(f"Processing file: {file_path}")

        # Read the CSV file in chunks
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            if len(chunk) <= sample_size:
                sample = chunk  # If batch is small, take the whole thing
            else:
                sample = chunk.sample(n=sample_size)
            all_samples.append(sample)

# Combine all samples into one DataFrame
final_df = pd.concat(all_samples, ignore_index=True)

# Save to a Parquet file
final_df.to_parquet(output_parquet, engine="pyarrow")
print(f" All samples saved to: {output_parquet}")
