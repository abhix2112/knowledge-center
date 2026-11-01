"""Turn uploaded files (PDF, DOCX, Markdown, text) into markdown text."""

from io import BytesIO

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


class UnsupportedFile(Exception):
    """The file isn't one of the supported types, or its content doesn't match its extension."""


def extract_text(data: bytes, extension: str) -> str:
    if extension == ".pdf":
        if not data.startswith(b"%PDF"):
            raise UnsupportedFile("This file has a .pdf extension but isn't a PDF")
        return pdf_to_text(data)
    if extension == ".docx":
        if not data.startswith(b"PK"):  # .docx files are zip archives
            raise UnsupportedFile("This file has a .docx extension but isn't a Word document")
        return docx_to_markdown(data)
    if extension in {".md", ".txt"}:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            raise UnsupportedFile("Text files must be UTF-8") from None
    raise UnsupportedFile(f"Unsupported file type: {extension}")


def pdf_to_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(page.strip() for page in pages if page.strip())


def docx_to_markdown(data: bytes) -> str:
    """Keep the structure we can: Word headings become #, list items become -."""
    lines = []
    for paragraph in Document(BytesIO(data)).paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = paragraph.style.name if paragraph.style is not None else ""
        if style.startswith("Heading "):
            level = style.removeprefix("Heading ")
            hashes = "#" * int(level) if level.isdigit() else "#"
            lines.append(f"{hashes} {text}")
        elif style == "Title":
            lines.append(f"# {text}")
        elif style.startswith("List"):
            lines.append(f"- {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines)


def split_title(text: str, fallback_title: str) -> tuple[str, str]:
    """Use the first '# Heading' as the title and remove it from the body.

    Without a heading, use the fallback (the filename) and keep the body as is.
    """
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("# "):
        title = lines[0].removeprefix("# ").strip()
        body = "\n".join(lines[1:]).strip()
        if title and body:
            return title, body
    return fallback_title, text.strip()
