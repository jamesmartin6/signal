"""CSV parsing for the lead-upload endpoint.

Kept independent of FastAPI so it's trivially unit-testable and reusable
(e.g. from a future CLI import tool).
"""

import csv
import io
from dataclasses import dataclass, field

REQUIRED_COLUMNS = {"name", "company", "bio_or_linkedin_url"}


class CSVValidationError(ValueError):
    """Raised for file-level problems (empty file, missing header/columns)."""


@dataclass
class ParsedRow:
    name: str
    company: str
    bio_or_linkedin_url: str
    raw: dict[str, str]


@dataclass
class SkippedRow:
    row_number: int
    reason: str
    raw: dict[str, str]


@dataclass
class CSVParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    skipped: list[SkippedRow] = field(default_factory=list)


def parse_leads_csv(content: bytes) -> CSVParseResult:
    """Parse an uploaded CSV of leads.

    Expected columns (case-insensitive, any order): name, company,
    bio_or_linkedin_url. Rows missing a required value are skipped (not
    fatal) and reported back to the caller; file-level problems (empty file,
    missing header, missing required columns) raise CSVValidationError.
    """
    text = content.decode("utf-8-sig", errors="replace").strip()
    if not text:
        raise CSVValidationError("CSV file is empty.")

    raw_reader = csv.reader(io.StringIO(text))
    try:
        header_row = next(raw_reader)
    except StopIteration as exc:
        raise CSVValidationError("CSV file has no header row.") from exc

    normalized_header = [h.strip().lower() for h in header_row]
    missing = REQUIRED_COLUMNS - set(normalized_header)
    if missing:
        raise CSVValidationError(
            f"CSV is missing required column(s): {', '.join(sorted(missing))}. "
            f"Expected columns: {', '.join(sorted(REQUIRED_COLUMNS))}."
        )

    result = CSVParseResult()
    row_number = 1  # header is row 1; data starts at row 2
    for fields in raw_reader:
        row_number += 1
        if not any(f.strip() for f in fields):
            continue  # blank line, silently ignored

        row_dict = dict(zip(normalized_header, fields, strict=False))
        name = (row_dict.get("name") or "").strip()
        bio = (row_dict.get("bio_or_linkedin_url") or "").strip()
        company = (row_dict.get("company") or "").strip()

        if not name or not bio:
            result.skipped.append(
                SkippedRow(
                    row_number=row_number,
                    reason="missing required value for 'name' or 'bio_or_linkedin_url'",
                    raw=row_dict,
                )
            )
            continue

        result.rows.append(ParsedRow(name=name, company=company, bio_or_linkedin_url=bio, raw=row_dict))

    if not result.rows and not result.skipped:
        raise CSVValidationError("CSV has a header row but no data rows.")

    return result
