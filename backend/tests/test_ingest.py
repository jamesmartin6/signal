import pytest

from app.ingest import CSVValidationError, parse_leads_csv

VALID_CSV = b"""name,company,bio_or_linkedin_url
Jane Doe,Acme Corp,"Senior VP of Engineering at Acme Corp, 15 years in fintech."
John Smith,Beta Inc,"Software engineer at Beta Inc working on backend systems."
"""


def test_parses_valid_rows():
    result = parse_leads_csv(VALID_CSV)
    assert len(result.rows) == 2
    assert result.skipped == []
    assert result.rows[0].name == "Jane Doe"
    assert result.rows[0].company == "Acme Corp"


def test_header_case_and_whitespace_insensitive():
    csv_bytes = b" Name , Company , Bio_Or_LinkedIn_URL \nJane,Acme,A great bio\n"
    result = parse_leads_csv(csv_bytes)
    assert len(result.rows) == 1
    assert result.rows[0].name == "Jane"


def test_empty_file_raises():
    with pytest.raises(CSVValidationError, match="empty"):
        parse_leads_csv(b"")


def test_whitespace_only_file_raises():
    with pytest.raises(CSVValidationError, match="empty"):
        parse_leads_csv(b"   \n  \n")


def test_missing_required_column_raises():
    csv_bytes = b"name,company\nJane,Acme\n"
    with pytest.raises(CSVValidationError, match="missing required column"):
        parse_leads_csv(csv_bytes)


def test_header_only_no_data_rows_raises():
    csv_bytes = b"name,company,bio_or_linkedin_url\n"
    with pytest.raises(CSVValidationError, match="no data rows"):
        parse_leads_csv(csv_bytes)


def test_malformed_row_missing_name_is_skipped_not_fatal():
    csv_bytes = (
        b"name,company,bio_or_linkedin_url\n"
        b",Acme,Some bio text\n"
        b"Jane Doe,Acme,Another bio\n"
    )
    result = parse_leads_csv(csv_bytes)
    assert len(result.rows) == 1
    assert len(result.skipped) == 1
    assert result.skipped[0].row_number == 2
    assert result.rows[0].name == "Jane Doe"


def test_malformed_row_missing_bio_is_skipped():
    csv_bytes = b"name,company,bio_or_linkedin_url\nJane Doe,Acme,\n"
    result = parse_leads_csv(csv_bytes)
    assert len(result.rows) == 0
    assert len(result.skipped) == 1


def test_blank_lines_are_ignored_silently():
    csv_bytes = (
        b"name,company,bio_or_linkedin_url\n"
        b"\n"
        b"Jane Doe,Acme,A bio\n"
        b"\n"
    )
    result = parse_leads_csv(csv_bytes)
    assert len(result.rows) == 1
    assert len(result.skipped) == 0


def test_ragged_row_missing_trailing_column_treated_as_empty():
    csv_bytes = b"name,company,bio_or_linkedin_url\nJane Doe,Acme\n"
    result = parse_leads_csv(csv_bytes)
    assert len(result.rows) == 0
    assert len(result.skipped) == 1
    assert "bio_or_linkedin_url" in result.skipped[0].reason
