import pdfplumber


def extract_text_from_pdf(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


def pdf_page_count(path: str) -> int:
    with pdfplumber.open(path) as pdf:
        return max(1, len(pdf.pages))
