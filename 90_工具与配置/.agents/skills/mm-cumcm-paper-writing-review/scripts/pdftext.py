# -*- coding: utf-8 -*-
"""Extract text from a CUMCM paper PDF (pypdf-based).

Usage:
    py pdftext.py <paper.pdf>            # all pages' text
    py pdftext.py <paper.pdf> 1 3        # from page 1, read 3 pages (1-based)

Notes:
    - Scanned PDFs have no text layer -> empty output; read them visually instead.
    - Used by the mm-cumcm-paper-writing-review skill to inspect abstracts/rubrics.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pypdf import PdfReader

path = sys.argv[1]
start = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0
count = int(sys.argv[3]) if len(sys.argv) > 3 else 10**6

reader = PdfReader(path)
total = len(reader.pages)
print(f"[pages: {total}]")
for i in range(start, min(start + count, total)):
    text = reader.pages[i].extract_text() or ""
    print(f"\n===== page {i + 1} =====")
    print(text.strip()[:6000])
