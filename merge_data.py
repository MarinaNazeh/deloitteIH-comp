import pandas as pd

# Quick merge version
def quick_merge(merged_orders_path, dim_places_path):
    """Simple merge of orders with store data"""
    
    # Load data
    merged_orders = pd.read_csv(merged_orders_path, low_memory=False)
    dim_places = pd.read_csv(dim_places_path, low_memory=False)
    
    # Clean place_id
    merged_orders['place_id'] = pd.to_numeric(merged_orders['place_id'], errors='coerce')
    dim_places['id'] = pd.to_numeric(dim_places['id'], errors='coerce')
    
    # Merge
    result = pd.merge(
        merged_orders,
        dim_places,
        left_on='place_id',
        right_on='id',
        how='left',
        suffixes=('', '_store')
    )
    
    # Save
    result.to_csv('merged_complete.csv', index=False)
    print(f"✅ Saved {len(result):,} records to merged_complete.csv")
    
    return result

# Run it
complete_data = quick_merge("cleaned_merged_order.csv", "dim_places.csv")