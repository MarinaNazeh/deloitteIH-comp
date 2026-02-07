"""
Split merged_complete.csv into 10 smaller parts.
Uses streaming with csv module to handle large file and quoted newlines.
"""
import csv
import os

INPUT_FILE = "merged_complete.csv"
OUTPUT_PREFIX = "merged_complete_part"
NUM_PARTS = 10

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    input_path = os.path.join(base_dir, INPUT_FILE)
    if not os.path.exists(input_path):
        input_path = os.path.join(data_dir, INPUT_FILE)
    if not os.path.exists(input_path):
        print(f"Error: {INPUT_FILE} not found in {base_dir} or {data_dir}")
        return
    os.makedirs(data_dir, exist_ok=True)

    # Open 10 output files and csv writers (write to data/)
    writers = []
    handles = []
    for i in range(NUM_PARTS):
        out_path = os.path.join(data_dir, f"{OUTPUT_PREFIX}{i + 1}.csv")
        f = open(out_path, "w", newline="", encoding="utf-8")
        handles.append(f)
        writers.append(csv.writer(f))

    try:
        with open(input_path, "r", newline="", encoding="utf-8") as infile:
            reader = csv.reader(infile)
            header = next(reader)

            # Write header to all parts
            for w in writers:
                w.writerow(header)

            # Distribute rows round-robin to the 10 parts
            for row_index, row in enumerate(reader):
                part_index = row_index % NUM_PARTS
                writers[part_index].writerow(row)

            if (row_index + 1) % 500_000 == 0 or row_index < 10:
                print(f"Processed {row_index + 1} rows...")

        print(f"Done. Total data rows: {row_index + 1}")
        print(f"Created: data/{OUTPUT_PREFIX}1.csv through data/{OUTPUT_PREFIX}{NUM_PARTS}.csv")
    finally:
        for f in handles:
            f.close()

if __name__ == "__main__":
    main()
