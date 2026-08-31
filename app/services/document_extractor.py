from pypdf import PdfReader
from docx import Document as DocxDocument
from io import BytesIO


SUPPORTED_TYPES = {"pdf", "docx", "txt"}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = DocxDocument(BytesIO(file_bytes))
    text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    return text.strip()


def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8").strip()


def get_file_extension(filename: str) -> str:
    extension = filename.lower().split(".")[-1]
    if extension not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported file type: {extension}")
    return extension


def extract_text(filename: str, file_bytes: bytes) -> str:
    extension = get_file_extension(filename)

    if extension == "pdf":
        text = extract_text_from_pdf(file_bytes)
    elif extension == "docx":
        text = extract_text_from_docx(file_bytes)
    else:
        text = extract_text_from_txt(file_bytes)

    if not text:
        raise ValueError("No extractable text found in document")

    return text