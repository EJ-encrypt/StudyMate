from pptx import Presentation


def extract_text_from_pptx(path: str) -> str:
    presentation = Presentation(path)

    slides = []
    for index, slide in enumerate(presentation.slides, start=1):
        lines = [
            shape.text.strip()
            for shape in slide.shapes
            if shape.has_text_frame and shape.text.strip()
        ]
        if lines:
            slides.append(f"Slide {index}\n" + "\n".join(lines))

    return "\n\n".join(slides)
