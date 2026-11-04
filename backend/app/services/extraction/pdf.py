import pdfplumber


def extract_text_from_pdf(path: str) -> str:
    # Each page starts with "Page N", like "Slide N" for slides, so the Coach
    # can point a student to where a concept is explained.
    with pdfplumber.open(path) as pdf:
        return "\n\n".join(
            f"Page {number}\n{page.extract_text() or ''}" for number, page in enumerate(pdf.pages, start=1)
        )


def pdf_page_count(path: str) -> int:
    with pdfplumber.open(path) as pdf:
        return max(1, len(pdf.pages))
