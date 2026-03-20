# ticket-categorizer

## What it does
Reads incoming messages from a CSV file and automatically categorizes them into:
- Sales leads
- Support requests
- General inquiries

## Example
A small service company receives dozens of client emails daily.  
Instead of manually sorting them, the ticket categorizer script automatically organizes incoming messages into actionable categories.

## How to use
###Parse Email content to csv format
###Define email.csv file location
Change the input variable of config.py to your email.csv file location
###Define output file location (Optional)
Change the output variable og config.py to your desired file location
### Run script
python ticket_categorizer.py
