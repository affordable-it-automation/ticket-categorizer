import csv
import os
from pathlib import Path

sales_keywords = ["pricing", "quote", "services", "automation"]
support_keywords = ["error", "broken", "issue", "help", "password"]
project_root = Path(__file__).resolve().parent.parent
input_file = project_root / "data" / "sample_emails.csv"
output_dir = project_root / "output"

sales = []
support = []
general = []

with input_file.open(newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for row in reader:
        text = (row["subject"] + row["message"]).lower()

        if any(word in text for word in sales_keywords):
            sales.append(row)

        elif any(word in text for word in support_keywords):
            support.append(row)

        else:
            general.append(row)

def write_file(filename, rows):
    os.makedirs(output_dir, exist_ok=True)

    with (output_dir / filename).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["email","subject","message"])
        writer.writeheader()
        writer.writerows(rows)

write_file("sales_leads.csv", sales)
write_file("support_tickets.csv", support)
write_file("general_inquiries.csv", general)

print("Emails categorized successfully.")
