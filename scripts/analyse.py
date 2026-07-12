import pandas as pd

data = pd.read_csv("data/activities.csv")

print("Aantal activiteiten:")
print(len(data))

print("\nKolommen:")
print(data.columns.tolist())
