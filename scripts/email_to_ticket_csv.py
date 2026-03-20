import argparse
import csv
import json
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path


FIELDNAMES = ["email", "subject", "message"]
SUPPORTED_EXTENSIONS = {".eml", ".txt"}
DEFAULT_OUTPUT = "data/sample_emails.csv"
DEFAULT_CONFIG = "config/email_to_ticket_csv.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert email files into a CSV formatted for ticket_catagorizer.py."
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        help="Path to an email file or a directory containing email files.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG,
        help=f"Optional JSON config file. Defaults to {DEFAULT_CONFIG}.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=f"CSV file to create or update. Defaults to {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        default=None,
        help="Overwrite the output CSV instead of merging with existing rows.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=None,
        help="Search subdirectories when input_path is a directory.",
    )
    return parser.parse_args()


def resolve_project_path(raw_path, project_root):
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def load_config(config_path):
    if not config_path.exists():
        return {}

    with config_path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    if not isinstance(config, dict):
        raise ValueError("Config file must contain a JSON object.")

    return config


def get_setting(cli_value, config, key, default=None):
    if cli_value is not None:
        return cli_value
    return config.get(key, default)


def collect_email_files(input_path, recursive=False):
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        return [path]

    pattern = "**/*" if recursive else "*"
    files = [
        candidate
        for candidate in path.glob(pattern)
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        raise FileNotFoundError(f"No supported email files found in: {path}")

    return sorted(files)


def extract_body(message):
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_filename():
                continue
            if part.get_content_type() not in {"text/plain", "text/html"}:
                continue
            try:
                parts.append(part.get_content())
            except Exception:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                parts.append(payload.decode(charset, errors="replace"))
        return normalize_whitespace("\n".join(parts))

    try:
        content = message.get_content()
    except Exception:
        payload = message.get_payload(decode=True) or b""
        charset = message.get_content_charset() or "utf-8"
        content = payload.decode(charset, errors="replace")

    return normalize_whitespace(content)


def normalize_whitespace(text):
    lines = [line.strip() for line in str(text).splitlines()]
    cleaned = [line for line in lines if line]
    return "\n".join(cleaned)


def parse_structured_email(file_path):
    with file_path.open("rb") as source:
        message = BytesParser(policy=policy.default).parse(source)

    sender = parseaddr(message.get("From", ""))[1].strip()
    subject = str(message.get("Subject", "")).strip()
    body = extract_body(message)

    return {
        "email": sender,
        "subject": subject,
        "message": body,
    }


def parse_plain_text_email(file_path):
    text = file_path.read_text(encoding="utf-8", errors="replace")
    headers, _, body = text.partition("\n\n")

    sender = ""
    subject = ""
    for line in headers.splitlines():
        lower_line = line.lower()
        if lower_line.startswith("from:"):
            sender = parseaddr(line.split(":", 1)[1].strip())[1]
        elif lower_line.startswith("subject:"):
            subject = line.split(":", 1)[1].strip()

    if not body.strip():
        body = text

    return {
        "email": sender.strip(),
        "subject": subject.strip(),
        "message": normalize_whitespace(body),
    }


def parse_email_file(file_path):
    if file_path.suffix.lower() == ".txt":
        return parse_plain_text_email(file_path)
    return parse_structured_email(file_path)


def load_existing_rows(output_path):
    if not output_path.exists():
        return []

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {field: row.get(field, "").strip() for field in FIELDNAMES}
            for row in reader
        ]


def merge_rows(existing_rows, new_rows):
    merged = []
    seen = set()

    for row in existing_rows + new_rows:
        normalized = {field: row.get(field, "").strip() for field in FIELDNAMES}
        row_key = tuple(normalized[field] for field in FIELDNAMES)
        if row_key in seen:
            continue
        seen.add(row_key)
        merged.append(normalized)

    return merged


def write_rows(output_path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    config_path = resolve_project_path(args.config, project_root)
    config = load_config(config_path)

    input_value = args.input_path or config.get("input_path")
    if not input_value:
        raise ValueError(
            "No input path provided. Pass input_path on the command line or set input_path in the config file."
        )

    recursive = bool(get_setting(args.recursive, config, "recursive", False))
    replace = bool(get_setting(args.replace, config, "replace", False))
    output_value = get_setting(args.output, config, "output", DEFAULT_OUTPUT)
    input_path = resolve_project_path(input_value, project_root)
    output_path = resolve_project_path(output_value, project_root)

    email_files = collect_email_files(input_path, recursive=recursive)
    new_rows = [parse_email_file(file_path) for file_path in email_files]

    if replace:
        final_rows = merge_rows([], new_rows)
    else:
        existing_rows = load_existing_rows(output_path)
        final_rows = merge_rows(existing_rows, new_rows)

    write_rows(output_path, final_rows)
    print(
        f"Wrote {len(new_rows)} email file(s) to {output_path}."
        f" CSV now contains {len(final_rows)} row(s)."
    )


if __name__ == "__main__":
    main()
