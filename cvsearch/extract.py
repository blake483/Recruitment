"""Turn uploaded CV files (PDF, DOCX, DOC, RTF, TXT) into plain text."""

import os
import shutil
import subprocess
import tempfile

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".rtf", ".txt", ".odt"}


class ExtractionError(Exception):
    pass


def extract_text(path):
    text = _extract(path)
    return text.replace("\x00", "").replace("\u00a0", " ").replace("\u200b", "")


def _extract(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _pdf(path)
    if ext == ".docx":
        return _docx(path)
    if ext == ".txt":
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    if ext in {".doc", ".rtf", ".odt"}:
        return _via_libreoffice(path)
    raise ExtractionError(f"Unsupported file type: {ext}")


def _pdf(path):
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as e:  # pypdf raises a variety of errors on broken files
        raise ExtractionError(f"Could not read PDF: {e}") from e
    return "\n".join(pages)


def _docx(path):
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = docx.Document(path)
    except Exception as e:
        raise ExtractionError(f"Could not read Word file: {e}") from e
    # Contact details often live in the page header.
    parts = [p.text for section in document.sections for p in section.header.paragraphs]
    # Walk paragraphs and tables in document order - many CVs lay out roles
    # in tables, and the order matters for telling experience from education.
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            parts.append(Paragraph(child, document).text)
        elif child.tag.endswith("}tbl"):
            parts.extend(_table_lines(Table(child, document)))
    return "\n".join(parts)


def _table_lines(table):
    lines = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            text = cell.text.strip()
            if text and text not in cells:  # merged cells repeat their text
                cells.append(text)
        # Put each cell's last line next to the other cells, so a date column
        # ends up on the same line as the job title.
        if len(cells) > 1:
            first = cells[0].split("\n")
            lines.extend(first[:-1])
            lines.append("  |  ".join([first[-1]] + cells[1:]))
        else:
            lines.extend(cells)
    return lines


def _via_libreoffice(path):
    """Legacy .doc / .rtf need LibreOffice (free) installed to convert."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise ExtractionError(
            "Legacy .doc/.rtf files need LibreOffice installed "
            "(https://www.libreoffice.org). Alternatively re-save the file as .docx or .pdf."
        )
    with tempfile.TemporaryDirectory() as out:
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "txt:Text", "--outdir", out, path],
                check=True, capture_output=True, timeout=120,
            )
        except (subprocess.SubprocessError, OSError) as e:
            raise ExtractionError(f"LibreOffice conversion failed: {e}") from e
        txt = os.path.join(out, os.path.splitext(os.path.basename(path))[0] + ".txt")
        if not os.path.exists(txt):
            raise ExtractionError("LibreOffice produced no output")
        with open(txt, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
