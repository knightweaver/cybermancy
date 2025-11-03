import csv
import os
from openai import OpenAI
from dotenv import load_dotenv
import random

# Initialize API
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise SystemExit("Missing OPENAI_API_KEY (set in environment or .env)")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TONES = [
    "high-end corporate brochure tone with restrained poetry",
    "combat-veteran testimonial blended with technical detail",
    "black-market ad rewritten by a perfectionist engineer",
    "clinical medical catalog with a whisper of menace",
    "luxury product description written for mercenaries"
]

# -------------------------------
# Prompt generator
# -------------------------------
def build_prompt(name: str, desc: str, corp: str) -> str:
    tone = random.choice(TONES)
    return f"""
Write a single 2–8 word poetic blurb for a cybernetic implant.

Name: "{name}".
Effect: "{desc}"
Manufacturer: {corp}

Tone: {tone}
Do not exceed one short sentence.
"""


# -------------------------------
# API call
# -------------------------------
def get_blurb_from_openai(prompt: str) -> str:
    """Query GPT for a single blurb."""
    response = client.chat.completions.create(
        model="gpt-4o",  # or "gpt-4o" if available
        messages=[{"role": "system", "content": "You are a professional marketing writer in the Cybermancy universe."},
                  {"role": "user", "content": prompt}],
        max_tokens=180,
    )
    return response.choices[0].message.content.strip()


# -------------------------------
# Batch process CSV
# -------------------------------
def generate_blurbs(input_csv: str, output_csv: str):
    with open(input_csv, newline='', encoding='utf-8') as infile, \
         open(output_csv, 'w', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["marketing_blurb"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            name = row.get("cybernetic-upgrade-name", "")
            desc = row.get("description", "")
            corp = row.get("corp","")
            prompt = build_prompt(name, desc, corp)

            print(f"Generating blurb for {name} ({corp})...")
            try:
                blurb = get_blurb_from_openai(prompt)
            except Exception as e:
                print(f"⚠️ Error generating blurb for {name}: {e}")
                blurb = "Error generating blurb."

            row["marketing_blurb"] = blurb
            writer.writerow(row)

    print(f"\n✅ Completed! Enhanced file written to {output_csv}")


# -------------------------------
# Example usage
# -------------------------------
if __name__ == "__main__":
    input_file = "cybernetics-list-gpt.trimmed.csv"
    output_file = "cybernetics-marketing-ai.csv"
    generate_blurbs(input_file, output_file)
