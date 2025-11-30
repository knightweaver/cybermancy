import json
import pandas as pd

json_path = "loot_cybermancy_generated.json"
csv_out_path = "loot_cybermancy_generated.csv"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

records = []
for d in data:
    records.append({
        "old_name": d.get("new_name", ""),  # placeholder since no original name
        "new_name": d.get("new_name", ""),
        "new_description": d.get("new_description", ""),
        "img": d.get("img", ""),
        "effect": d.get("effect", "loot"),
        "img-path": f"modules/cybermancy/assets/icons/loot/{d.get('img','')}.webp"
    })

df = pd.DataFrame(records)
df.to_csv(csv_out_path, index=False, encoding="utf-8-sig")

print(f"✅ CSV written: {csv_out_path}")
