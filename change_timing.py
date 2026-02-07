import pandas as pd

# ==== 1. Load your dataset ====
# change the filename to your real file name
df = pd.read_csv("fct_order_items.csv")

# ==== 2. Convert 3rd and 4th columns (index 2 and 3) ====
df.iloc[:, 2] = pd.to_datetime(df.iloc[:, 2], unit='s')
df.iloc[:, 3] = pd.to_datetime(df.iloc[:, 3], unit='s')

# ==== 3. Save to a new CSV file ====
df.to_csv("new_fct_order_items.csv", index=False)

print("✅ Conversion complete. Saved as converted_file.csv")