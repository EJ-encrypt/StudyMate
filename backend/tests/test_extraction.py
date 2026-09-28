import pytest
from docx import Document
from pptx import Presentation
from pptx.util import Inches

from app.services.extraction import UnsupportedDocumentType, extract_text


def test_extracts_docx_paragraphs_and_tables(tmp_path) -> None:
    path = tmp_path / "lecture.docx"
    document = Document()
    document.add_paragraph("Functional dependencies constrain attribute sets.")
    document.add_paragraph("")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "1NF"
    table.rows[0].cells[1].text = "Atomic values only"
    document.save(path)

    text = extract_text(str(path))

    assert "Functional dependencies constrain attribute sets." in text
    assert "1NF | Atomic values only" in text


def test_extracts_pptx_slide_text(tmp_path) -> None:
    path = tmp_path / "deck.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    slide.shapes.title.text = "Normalization"
    box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(4), Inches(1))
    box.text_frame.text = "Third normal form removes transitive dependencies."
    presentation.save(path)

    text = extract_text(str(path))

    assert "Slide 1" in text
    assert "Normalization" in text
    assert "Third normal form removes transitive dependencies." in text


@pytest.mark.parametrize("suffix", [".txt", ".md"])
def test_extracts_typed_notes(tmp_path, suffix: str) -> None:
    path = tmp_path / f"notes{suffix}"
    path.write_text("A candidate key is minimal.", encoding="utf-8")

    assert extract_text(str(path)) == "A candidate key is minimal."


def test_rejects_unsupported_extension(tmp_path) -> None:
    path = tmp_path / "audio.mp3"
    path.write_bytes(b"not a document")

    with pytest.raises(UnsupportedDocumentType):
        extract_text(str(path))
