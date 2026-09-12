import base64
import io
import re
import unicodedata
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import httpx
from typing import Dict, Any, Tuple, Optional
from PIL import Image
from backend.app.llm.client import llm_client

class DocumentParser:
    """
    Unified multimodal document parser supporting:
    - PDF (.pdf) via high-speed PyMuPDF text extraction with column-aware layout parsing and high-res vision fallback
    - Image (.png, .jpg, .jpeg, .webp) via Gemini Multimodal Vision
    - Plain text (.txt, .md)
    """

    @classmethod
    def extract_text(cls, file_bytes: bytes, filename: str = "", content_type: str = "") -> Tuple[str, str]:
        """
        Returns (extracted_text, detected_type)
        """
        fname = filename.lower()
        ctype = content_type.lower()

        # 1. Check if PDF
        if fname.endswith(".pdf") or "application/pdf" in ctype:
            return cls._extract_from_pdf(file_bytes), "pdf"

        # 2. Check if Image
        image_exts = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]
        if any(fname.endswith(ext) for ext in image_exts) or "image/" in ctype:
            return cls._extract_from_image(file_bytes, fname, ctype), "image"

        # 3. Default to text decoding
        try:
            return file_bytes.decode("utf-8").strip(), "text"
        except UnicodeDecodeError:
            try:
                return file_bytes.decode("latin-1").strip(), "text"
            except Exception:
                return str(file_bytes), "unknown"

    @classmethod
    def _extract_from_pdf(cls, file_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            # Check encryption
            if doc.is_encrypted:
                try:
                    doc.authenticate("")
                except Exception:
                    pass
                if doc.is_encrypted:
                    return "Error: This PDF is password-protected. Please upload an unprotected PDF."

            pages_text = []
            for page in doc:
                # Column-aware block extraction: prevents interleaving left and right columns
                blocks = page.get_text("blocks")
                text_blocks = [
                    b for b in blocks 
                    if len(b) >= 5 and (len(b) < 7 or b[6] == 0) and isinstance(b[4], str) and b[4].strip()
                ]

                page_width = page.rect.width
                has_two_columns = False
                col1 = []
                col2 = []

                if len(text_blocks) >= 4:
                    left_blocks = [b for b in text_blocks if b[2] <= page_width * 0.55]
                    right_blocks = [b for b in text_blocks if b[0] >= page_width * 0.40]
                    if len(left_blocks) >= 2 and len(right_blocks) >= 2 and (len(left_blocks) + len(right_blocks)) >= len(text_blocks) * 0.75:
                        has_two_columns = True
                        col1 = sorted(left_blocks, key=lambda b: (b[1], b[0]))
                        col2 = sorted(right_blocks, key=lambda b: (b[1], b[0]))

                if has_two_columns:
                    page_content = "\n\n".join([b[4].strip() for b in col1] + [b[4].strip() for b in col2])
                else:
                    sorted_blocks = sorted(text_blocks, key=lambda b: (b[1], b[0]))
                    page_content = "\n\n".join([b[4].strip() for b in sorted_blocks])

                if not page_content.strip():
                    page_content = page.get_text("text").strip()

                if page_content.strip():
                    pages_text.append(page_content.strip())

            combined = "\n\n".join(pages_text)

            # Direct fallback to standard PyMuPDF text if block extraction missed content
            if len(combined.strip()) < 35:
                direct_pages = [page.get_text("text").strip() for page in doc if page.get_text("text").strip()]
                direct_text = "\n\n".join(direct_pages)
                if len(direct_text) > len(combined):
                    combined = direct_text

            # Normalize ligatures, remove null bytes, clean up line-break hyphenation
            if combined:
                combined = unicodedata.normalize('NFKC', combined)
                combined = combined.replace('\x00', '')
                combined = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', combined)
                combined = re.sub(r'\n{3,}', '\n\n', combined)

            if len(combined.strip()) >= 35:
                return combined.strip()

            # If PDF has no digital text (scanned PDF), use vision at 150 DPI on up to 4 pages
            if llm_client.gemini_key and len(doc) > 0:
                scanned_pages = []
                for i in range(min(4, len(doc))):
                    pix = doc[i].get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    page_text = cls._call_gemini_vision(b64, "image/png")
                    if page_text and len(page_text.strip()) > 20:
                        scanned_pages.append(page_text.strip())
                if scanned_pages:
                    return "\n\n".join(scanned_pages)

            return combined.strip() if combined.strip() else "PDF contains no readable text."
        except Exception as e:
            print(f"[DocumentParser] PDF parsing error: {e}")
            return f"Error extracting PDF text: {e}"

    @classmethod
    def extract_candidate_meta(cls, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts candidate full name and email address from resume text if present.
        Handles multi-column headers, piped lines, and various standard resume header layouts.
        """
        name = None
        email = None

        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            email = email_match.group(0).strip().lower()

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:10]:
            # If line contains delimiters like '|', '•', ' - ', check the segments
            segments = re.split(r'[|•·\t]', line)
            candidate_segments = [segments[0].strip()] if len(segments) > 1 else [line.strip()]
            for cleaned in candidate_segments:
                if not cleaned:
                    continue
                words = cleaned.split()
                if (
                    "@" not in cleaned
                    and not any(kw in cleaned.lower() for kw in ["http", "linkedin", "github", "curriculum", "resume", "page ", "email", "phone", "summary", "profile"])
                    and not re.search(r'\d', cleaned)
                    and 2 <= len(words) <= 4
                    and len(cleaned) < 40
                    and all(w[0].isupper() for w in words if w.isalpha())
                ):
                    name = cleaned
                    break
            if name:
                break

        return name, email

    @classmethod
    def _extract_from_image(cls, file_bytes: bytes, filename: str, content_type: str) -> str:
        mime = "image/png"
        if "jpeg" in content_type or filename.endswith(".jpg") or filename.endswith(".jpeg"):
            mime = "image/jpeg"
        elif "webp" in content_type or filename.endswith(".webp"):
            mime = "image/webp"

        b64 = base64.b64encode(file_bytes).decode("utf-8")

        # 1. Use Gemini Vision if key is available
        if llm_client.gemini_key:
            extracted = cls._call_gemini_vision(b64, mime)
            if extracted:
                return extracted

        # Fallback if vision key is absent
        return (
            "[Image uploaded: Vision extraction requires Gemini API key. "
            "Please configure Gemini key or paste text manually.]"
        )

    @classmethod
    def _call_gemini_vision(cls, b64_data: str, mime_type: str) -> str:
        if not llm_client.gemini_key:
            return ""
        models_to_try = ["gemini-flash-latest", "gemini-3.6-flash", "gemini-2.5-flash"]
        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={llm_client.gemini_key}"
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                                {
                                    "text": (
                                        "You are an OCR and technical document digitization specialist. "
                                        "Extract all text, sections, bullet points, headers, and code from this document image verbatim. "
                                        "Preserve the original layout, structure, and technical terminology exactly. "
                                        "Do not add conversational preamble. Return only the extracted text."
                                    )
                                }
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.1}
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "candidates" in data and data["candidates"]:
                            parts = data["candidates"][0].get("content", {}).get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"].strip()
            except Exception as e:
                print(f"[DocumentParser] Gemini vision call error with {model}: {e}")
                continue
        return ""

