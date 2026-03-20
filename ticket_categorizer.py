import csv
import os

sales_keywords = ["pricing", "quote", "services", "automation"]
support_keywords = ["error", "broken", "issue", "help", "password"]

sales = []
support = []
general = []

with open("../data/sample_emails.csv") as file:
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
    os.makedirs("../output", exist_ok=True)

    with open(f"../output/{filename}", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["email","subject","message"])
        writer.writeheader()
        writer.writerows(rows)

write_file("sales_leads.csv", sales)
write_file("support_tickets.csv", support)
write_file("general_inquiries.csv", general)

print("Emails categorized successfully.")
