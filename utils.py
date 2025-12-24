import re

from PIL import Image

try:
    from pdf2image import convert_from_bytes

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def process_image(image_input):
    """
    The Airlock: Sanitizes and optimizes user images.
    Returns: (PIL.Image, status_message)
    """
    try:
        if isinstance(image_input, Image.Image):
            image = image_input
        else:
            image = Image.open(image_input)

        if image.mode in ("RGBA", "P", "LA"):
            image = image.convert("RGB")

        max_dimension = 1024
        if max(image.size) > max_dimension:
            image = image.copy()
            image.thumbnail((max_dimension, max_dimension))

        return image, "SUCCESS"
    except Exception as e:
        return None, f"IMG_ERROR: {e}"


def convert_pdf_to_image(pdf_bytes):
    """
    Converts the first page of a PDF into a PIL Image.
    Robustness: Handles missing Poppler by returning an error, not crashing.
    """
    if not PDF_SUPPORT:
        return None, "PDF support missing (module not found)."

    try:
        images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=1)
        if images:
            return images[0], "SUCCESS"
        return None, "PDF_EMPTY"
    except Exception as e:
        return None, f"PDF_ERROR: {e}"


def sanitize_latex(text: str) -> str:
    """
    Standardizes LaTeX delimiters for Streamlit.
    Turns into $$ for proper rendering.
    """
    if not text:
        return ""

    # LINTER PROOF REGEX (Standard Strings with Double Escaping)
    # We use "\\\\" to represent a single backslash in regex
    # We use "\\[" to represent a literal bracket

    # 1. Convert \[ ... \] to $$ ... $$
    text = re.sub("\\\\\\[(.*?)\\\\\\]", "$$\\1$$", text, flags=re.DOTALL)

    # 2. Convert \( ... \) to $ ... $
    text = re.sub("\\\\\\((.*?)\\\\\\)", "$\\1$", text, flags=re.DOTALL)

    text = text.replace("$$", "\n$$\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()
