import json

p = "cybermancy-rulebook-assembly-manifest-v1.1.json"

with open(p, encoding="utf-8") as f:
    m = json.load(f)

print("AUTHORED INPUT RECORD")
print("=====================")
for row in m.get("authoredInputs", []):
    if row.get("assemblyInputId") == "auth.gm-guide-index":
        print(json.dumps(row, indent=2))

print("\nALL OCCURRENCES")
print("===============")

def walk(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, f"{path}[{i}]")
    elif obj == "auth.gm-guide-index":
        print(path)

walk(m)