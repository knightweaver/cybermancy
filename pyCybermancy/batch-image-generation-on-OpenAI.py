# requirements: pip install openai pillow python-slugify
import os, json, base64, zipfile, time
from io import BytesIO
from slugify import slugify
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

INPUT_JSON = "Consumeables_image_requests_test.json"
OUT_DIR = "cybermancy_icons_batch2"
ZIP_PATH = "cybermancy_icons_batch1.zip"
MODEL = "gpt-image-1"  # OpenAI Images model
SIZE = "1024x1024"

# Load API key from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Missing OPENAI_API_KEY in .env")

client = OpenAI(api_key=api_key)

# Color scheme mapping (from your spec)
EFFECT_PALETTE = {
    "healing": "warm red–orange to amber",
    "stress": "soft violet-blue to lavender",
    "physical": "cyan–teal to electric blue",
    "strength": "amber-gold to bronze",
    "cognitive": "neon green to lime-white",
    "charisma": "neon green to lime-white"  # map charisma to cognitive look
}

# Shared style directive for consistency
STYLE = (
    "cyberpunk item icon, semi-realistic rendering, metallic/glass materials, "
    "clean silhouette, soft reflections, subtle vignette, NO text or labels, "
    "light grey background, consistent luminance"
)

def build_prompt(name, description, effect):
    palette = EFFECT_PALETTE.get(effect.lower().strip(), "cyan–teal to electric blue")
    return (
        f"{name}: {description}. "
        f"Color scheme: {palette}. "
        f"Style: {STYLE}."
    )

def save_webp_from_b64(b64_png, out_path):
    img_bytes = base64.b64decode(b64_png)
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    img.save(out_path, "WEBP", method=6, quality=95)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = json.load(open(INPUT_JSON, "r", encoding="utf-8"))
    client = OpenAI()  # needs OPENAI_API_KEY env var

    for item in data:
        name = item.get("name", "Unnamed")
        desc = item.get("description", "")
        effect = (item.get("effect") or "physical")
        prompt = build_prompt(name, desc, effect)

        # file name
        fn = f"{slugify(name)}.webp"
        out_file = os.path.join(OUT_DIR, fn)

        # Skip if already rendered (handy for retries)
        if os.path.exists(out_file):
            continue

        # Generate
        resp = client.images.generate(
            model=MODEL,
            prompt=prompt,
            size=SIZE
            # If supported in your runtime, you can add: seed=1234
        )
        b64 = resp.data[0].b64_json
        save_webp_from_b64(b64, out_file)

        # Gentle pacing to avoid rate limits
        time.sleep(1.0)

    # Zip output
    #with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    #    for fn in sorted(os.listdir(OUT_DIR)):
    #        if fn.lower().endswith(".webp"):
    #            z.write(os.path.join(OUT_DIR, fn), arcname=fn)

    print(f"Done.")

if __name__ == "__main__":
    main()
