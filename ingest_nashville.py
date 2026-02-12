import pandas as pd

# Load raw Nashville parcels
df = pd.read_csv("data/nashville/raw_parcels.csv")

# Rename required columns
df = df.rename(columns={
    "Parcel ID": "parcel_id",
    "Acres": "acres"
})

# Create lot_size in square feet
df["lot_size"] = df["acres"] * 43560

# Save minimally aligned file
df.to_csv("data/nashville/parcels.csv", index=False)

print("Nashville parcels.csv created successfully")
