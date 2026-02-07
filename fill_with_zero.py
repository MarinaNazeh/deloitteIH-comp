import pandas as pd

# load your dataset
df = pd.read_csv("merged_orders_robust.csv")

# ===== Fill NA values with 0 =====
zero_fill_columns = [
    "points_earned_item",
    "points_redeemed_item",
    "vat_amount_item",
    "updated_by",
    "cashier_notified",
    "demo_mode",
    "items_amount",
    "points_earned_order",
    "points_redeemed_order",
    "service_charge",
    "split_bill",
    "synchronized_to_accounting",
    "total_amount",
    "trainee_mode",
    "vat_amount_order"
]

df[zero_fill_columns] = df[zero_fill_columns].fillna(0)

# ===== Special case: discount_amount_order =====
# fill NA with minimum discount value in that column
min_discount = df["discount_amount_order"].min()
df["discount_amount_order"] = df["discount_amount_order"].fillna(min_discount)

# ===== Save cleaned dataset =====
df.to_csv("cleaned_merged_order.csv", index=False)

print("✅ Missing values handled and saved as cleaned_dataset.csv")