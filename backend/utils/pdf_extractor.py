# utils/pdf_extractor.py
# ─────────────────────────────────────────────────────────────
# Responsible ONLY for: reading a PDF file → returning clean text.
# We use pdfplumber because it handles multi-column layouts well
# and preserves spacing better than PyPDF2.
# ─────────────────────────────────────────────────────────────

import pdfplumber          # The PDF parsing library
import re                  # Regular expressions for cleaning text
from typing import Tuple   # For type hints on return values


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, int]:
    """
    Takes raw PDF bytes (from an uploaded file) and returns:
      - cleaned_text (str): all text on all pages combined
      - page_count (int): how many pages were in the PDF

    Why bytes? Because FastAPI gives us the file as bytes in memory,
    so we never need to save it to disk — more secure & faster.
    """

    all_text_parts = []   # We'll collect text per page here

    # pdfplumber.open() can accept a file-like object.
    # io.BytesIO wraps raw bytes so it behaves like a file.
    import io
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)  # total page count

        for page in pdf.pages:
            # extract_text() reads all visible text on that page
            # It returns None if the page is blank, so we guard with `or ""`
            page_text = page.extract_text() or ""
            all_text_parts.append(page_text)

    # Join all pages with a newline between them
    raw_text = "\n".join(all_text_parts)

    # Clean up the raw text before returning
    cleaned_text = _clean_text(raw_text)

    return cleaned_text, page_count


def _clean_text(text: str) -> str:
    """
    Private helper to remove junk characters from extracted PDF text.
    PDF extraction often gives us:
      - Multiple blank lines
      - Weird unicode characters
      - Trailing spaces on every line
    We fix all of that here so downstream code gets clean input.
    """

    # 1. Replace Windows line endings (\r\n) with Unix (\n)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Remove non-printable characters except tabs and newlines
    #    \x00-\x08 and \x0b-\x1f are control characters we don't need
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 3. Replace more than 2 consecutive newlines with exactly 2
    #    This collapses big blank gaps in the text
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. Strip trailing whitespace from each line
    lines = [line.strip() for line in text.splitlines()]

    # 5. Rejoin and strip leading/trailing whitespace from whole text
    return "\n".join(lines).strip()
