"""
extractor.py — Raw text extraction for PDF, DOCX, TXT and images (OCR).
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

PDF = {"application/pdf"}
DOCX = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"}
TEXT = {"text/plain", "text/markdown"}
IMAGE = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/tiff"}

SUPPORTED_MIME = PDF | DOCX | TEXT | IMAGE

EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

_ocr_reader = None


class ExtractorService:
    @staticmethod
    def extract_pdf_text(file_path: str) -> Tuple[str, int]:
        import pdfplumber

        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
            count = len(pdf.pages)
        text = "\n\n".join(pages).strip()
        if not text:
            # Scanned PDF: rasterise pages and OCR them.
            try:
                import pdfplumber

                with pdfplumber.open(file_path) as pdf:
                    parts = []
                    for page in pdf.pages[:20]:
                        img = page.to_image(resolution=200).original
                        parts.append(ExtractorService._ocr_pil(img))
                text = "\n\n".join(parts)
            except Exception as e:
                logger.warning("PDF OCR fallback failed: %s", e)
        return text, count

    @staticmethod
    def extract_docx_text(file_path: str) -> str:
        import docx

        d = docx.Document(file_path)
        parts = [p.text for p in d.paragraphs if p.text.strip()]
        for table in d.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n\n".join(parts)

    @staticmethod
    def extract_txt_text(file_path: str) -> str:
        with open(file_path, "rb") as f:
            raw = f.read()
        for enc in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _ocr_pil(img) -> str:
        """OCR a PIL image. Tesseract (eng+mal) is preferred for Malayalam; EasyOCR handles English."""
        try:
            import pytesseract

            langs = pytesseract.get_languages(config="")
            lang = "mal+eng" if "mal" in langs else "eng"
            return pytesseract.image_to_string(img, lang=lang)
        except Exception:
            pass
        global _ocr_reader
        import numpy as np

        if _ocr_reader is None:
            import easyocr

            _ocr_reader = easyocr.Reader(["en"], gpu=False)
        return "\n".join(t for _, t, _ in _ocr_reader.readtext(np.array(img)))

    @staticmethod
    def extract_image_text(file_path: str) -> str:
        from PIL import Image

        return ExtractorService._ocr_pil(Image.open(file_path).convert("RGB"))

    def extract(self, file_path: str, mime: str) -> Tuple[str, Optional[int], str]:
        """Returns (text, page_count, method)."""
        if mime in PDF:
            text, pages = self.extract_pdf_text(file_path)
            return text, pages, "pdfplumber"
        if mime in DOCX:
            return self.extract_docx_text(file_path), None, "python-docx"
        if mime in TEXT:
            return self.extract_txt_text(file_path), None, "plain text"
        if mime in IMAGE:
            return self.extract_image_text(file_path), 1, "OCR"
        raise ValueError(f"Unsupported file type: {mime}")


extractor_service = ExtractorService()
