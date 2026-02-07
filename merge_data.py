import pandas as pd
import numpy as np

# =============================================
# FIXED VERSION - HANDLES NULL VALUES
# =============================================

# Load files with specific dtypes to avoid warnings
print("📊 Loading data files...")

# Read with low_memory=False to handle mixed types
fct_order_items = pd.read_csv('new_fct_order_items.csv', low_memory=False)
fct_orders = pd.read_csv('new_fct_orders.csv', low_memory=False)

print(f"✅ Loaded {len(fct_order_items)} order items and {len(fct_orders)} orders")

# =============================================
# METHOD 1: SIMPLE MERGE (Handles nulls automatically)
# =============================================

print("\n" + "="*80)
print("METHOD 1: Simple Merge")
print("="*80)

# Simple merge - pandas handles nulls automatically
simple_merge = pd.merge(
    fct_order_items, 
    fct_orders, 
    left_on='order_id', 
    right_on='id',
    how='inner'  # Automatically excludes rows with null order_id
)

print(f"✅ Merged {len(simple_merge)} records")
print(f"Columns: {len(simple_merge.columns)}")

# =============================================
# METHOD 2: ROBUST MERGE WITH NULL HANDLING
# =============================================

print("\n" + "="*80)
print("METHOD 2: Robust Merge with Validation")
print("="*80)

def robust_merge_order_files(order_items_df, orders_df):
    """
    Safe merge that handles null values and data issues
    """
    
    # Create a copy to avoid modifying original
    order_items = order_items_df.copy()
    orders = orders_df.copy()
    
    # Check for null values in order_id
    null_order_ids = order_items['order_id'].isna().sum()
    print(f"Order items with null order_id: {null_order_ids}")
    
    # Check data types
    print(f"\nData types before cleaning:")
    print(f"order_id dtype: {order_items['order_id'].dtype}")
    print(f"id dtype: {orders['id'].dtype}")
    
    # Convert to string first to handle mixed types, then to numeric
    order_items['order_id_clean'] = pd.to_numeric(
        order_items['order_id'].astype(str), 
        errors='coerce'  # Convert non-numeric to NaN
    )
    
    orders['id_clean'] = pd.to_numeric(
        orders['id'].astype(str),
        errors='coerce'
    )
    
    # Check cleaned data
    print(f"\nAfter cleaning:")
    print(f"Valid order_ids: {order_items['order_id_clean'].notna().sum()}")
    print(f"Valid order master ids: {orders['id_clean'].notna().sum()}")
    
    # Find matching records
    valid_order_items = order_items[order_items['order_id_clean'].notna()]
    valid_orders = orders[orders['id_clean'].notna()]
    
    # Convert to integer (now safe since we removed NaNs)
    valid_order_items['order_id_int'] = valid_order_items['order_id_clean'].astype(int)
    valid_orders['id_int'] = valid_orders['id_clean'].astype(int)
    
    # Perform the merge
    merged = pd.merge(
        valid_order_items,
        valid_orders,
        left_on='order_id_int',
        right_on='id_int',
        how='inner',
        suffixes=('_item', '_order')
    )
    
    # Clean up temporary columns
    merged = merged.drop(['order_id_clean', 'id_clean', 'order_id_int', 'id_int'], axis=1, errors='ignore')
    
    # Summary statistics
    print(f"\n📊 Merge Results:")
    print(f"Total order items: {len(order_items)}")
    print(f"Valid order items (non-null order_id): {len(valid_order_items)}")
    print(f"Valid orders (non-null id): {len(valid_orders)}")
    print(f"Successfully merged: {len(merged)} records")
    print(f"Merge success rate: {len(merged)/len(valid_order_items)*100:.1f}%")
    
    return merged

# Execute robust merge
merged_data = robust_merge_order_files(fct_order_items, fct_orders)

# =============================================
# METHOD 3: QUICK & DIRTY (If you just want it to work)
# =============================================

print("\n" + "="*80)
print("METHOD 3: Quick & Dirty Solution")
print("="*80)

# Even simpler approach - just drop nulls first
quick_merge = pd.merge(
    fct_order_items.dropna(subset=['order_id']),  # Remove rows with null order_id
    fct_orders.dropna(subset=['id']),             # Remove rows with null id
    left_on='order_id',
    right_on='id',
    how='inner'
)

print(f"✅ Quick merge: {len(quick_merge)} records")

# =============================================
# ANALYSIS OF MERGED DATA
# =============================================

print("\n" + "="*80)
print("ANALYSIS OF MERGED DATA")
print("="*80)

if len(merged_data) > 0:
    print(f"\n📊 Sample of merged data (first 3 rows):")
    
    # Select key columns for inventory analysis
    key_columns = ['order_id', 'title', 'quantity', 'price', 'cost', 
                   'place_id', 'total_amount', 'created_order', 'channel', 'type']
    
    # Find which columns actually exist
    available_columns = [col for col in key_columns if col in merged_data.columns]
    
    print(merged_data[available_columns].head(3))
    
    # Basic statistics
    print(f"\n📈 Basic Statistics:")
    print(f"Total revenue: ${merged_data['total_amount'].sum():,.2f}")
    print(f"Average order value: ${merged_data['total_amount'].mean():,.2f}")
    print(f"Total items sold: {merged_data['quantity'].sum():,.0f}")
    
    # Check for demo mode orders (important for inventory)
    if 'demo_mode' in merged_data.columns:
        demo_count = (merged_data['demo_mode'] == 1).sum()
        print(f"Demo/training orders: {demo_count} ({demo_count/len(merged_data)*100:.1f}%)")
    
    # Check order status
    if 'status_order' in merged_data.columns:
        status_counts = merged_data['status_order'].value_counts()
        print(f"\n📋 Order Status Distribution:")
        for status, count in status_counts.head().items():
            print(f"  {status}: {count} ({count/len(merged_data)*100:.1f}%)")

# =============================================
# SAVE THE MERGED DATA
# =============================================

print("\n" + "="*80)
print("SAVING RESULTS")
print("="*80)

# Save all three versions if you want
merged_data.to_csv('merged_orders_robust.csv', index=False)
simple_merge.to_csv('merged_orders_simple.csv', index=False)
quick_merge.to_csv('merged_orders_quick.csv', index=False)

print("✅ Saved merged files:")
print("   - merged_orders_robust.csv")
print("   - merged_orders_simple.csv")
print("   - merged_orders_quick.csv")

# =============================================
# BONUS: ONE-LINER SOLUTION
# =============================================

print("\n" + "="*80)
print("BONUS: One-Liner Solution")
print("="*80)

# If you want the absolute simplest working solution:
try:
    one_liner = pd.merge(
        fct_order_items.dropna(subset=['order_id']).astype({'order_id': 'int64'}),
        fct_orders.dropna(subset=['id']).astype({'id': 'int64'}),
        left_on='order_id',
        right_on='id'
    )
    print(f"✅ One-liner merge: {len(one_liner)} records")
except Exception as e:
    print(f"⚠️  One-liner failed: {e}")
    print("Using the robust method instead...")