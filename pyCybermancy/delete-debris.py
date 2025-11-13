import os

target = "rex-ghostwire-mendez.md"
root = "."

for dirpath, _, filenames in os.walk(root):
    if target in filenames:
        fp = os.path.join(dirpath, target)
        try:
            os.remove(fp)
            print(f"deleted: {fp}")
        except OSError as e:
            print(f"error deleting {fp}: {e}")