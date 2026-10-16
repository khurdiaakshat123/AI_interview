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

        # 2. Check if Word Document (DOCX)
        if fname.endswith(".docx") or "officedocument.wordprocessingml" in ctype or "application/msword" in ctype or fname.endswith(".doc"):
            return cls._extract_from_docx(file_bytes), "docx"

        # 3. Check if Image
        image_exts = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]
        if any(fname.endswith(ext) for ext in image_exts) or "image/" in ctype:
            return cls._extract_from_image(file_bytes, fname, ctype), "image"

        # 4. Default to text decoding (TXT, MD, CSV, etc.)
        try:
            return file_bytes.decode("utf-8").strip(), "text"
        except UnicodeDecodeError:
            try:
                return file_bytes.decode("latin-1").strip(), "text"
            except Exception:
                return str(file_bytes), "unknown"

    @classmethod
    def _extract_page_layout_text(cls, page) -> str:
        """
        Extracts text from a PDF page respecting physical 2D reading order.
        Groups words into horizontal lines by baseline coordinate clustering,
        preventing multi-stream font layering (e.g. bold keywords rendered in separate streams)
        from splitting sentences into disjoint blocks.
        """
        try:
            words = page.get_text("words", sort=True)
            if not words:
                return page.get_text("text").strip()

            page_width = page.rect.width

            # Detect two-column layout
            left_words = [w for w in words if w[2] <= page_width * 0.52]
            right_words = [w for w in words if w[0] >= page_width * 0.48]
            has_two_cols = (
                len(left_words) >= 15 and len(right_words) >= 15 and
                (len(left_words) + len(right_words)) >= len(words) * 0.85
            )

            def cluster_words_to_lines(word_list):
                if not word_list:
                    return []
                # Group words with vertical baseline tolerance of 3.5 points
                lines_dict = {}
                for w in word_list:
                    # w: (x0, y0, x1, y1, word, block_no, line_no, word_no)
                    y_key = round(w[1] / 3.5) * 3.5
                    lines_dict.setdefault(y_key, []).append((w[0], w[4]))

                result_lines = []
                for y in sorted(lines_dict.keys()):
                    row = sorted(lines_dict[y], key=lambda x: x[0])
                    line_str = " ".join(t for _, t in row).strip()
                    if line_str:
                        result_lines.append(line_str)
                return result_lines

            if has_two_cols:
                col1_lines = cluster_words_to_lines(left_words)
                col2_lines = cluster_words_to_lines(right_words)
                return "\n".join(col1_lines) + "\n\n" + "\n".join(col2_lines)
            else:
                lines = cluster_words_to_lines(words)
                return "\n".join(lines)
        except Exception:
            return page.get_text("text").strip()

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
                # 1. Use 2D spatial word-clustering to prevent bold font layers from de-interleaving text
                page_content = cls._extract_page_layout_text(page)

                # Fallback to column-aware blocks if word extraction was too sparse
                if len(page_content.strip()) < 30:
                    blocks = page.get_text("blocks")
                    text_blocks = [
                        b for b in blocks 
                        if len(b) >= 5 and (len(b) < 7 or b[6] == 0) and isinstance(b[4], str) and b[4].strip()
                    ]
                    if text_blocks:
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
            if len(doc) > 0:
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

        # 1. Use Gemini Vision via key_pool
        extracted = cls._call_gemini_vision(b64, mime)
        if extracted and len(extracted.strip()) > 20:
            return extracted

        # Fallback if vision extraction fails
        return (
            "[Image uploaded: Vision extraction requires active Gemini API key. "
            "Please configure Gemini key or paste text manually.]"
        )

    @classmethod
    def _extract_from_docx(cls, file_bytes: bytes) -> str:
        """
        Extracts plain text paragraphs from Microsoft Word (.docx) documents.
        Directly parses word/document.xml without external dependencies.
        """
        import zipfile
        import xml.etree.ElementTree as ET
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                if "word/document.xml" not in zf.namelist():
                    return "Error: Invalid DOCX archive format."
                xml_data = zf.read("word/document.xml")
                root = ET.fromstring(xml_data)
                
                w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                paragraphs = []
                for p in root.iter(f"{{{w_ns}}}p"):
                    texts = [t.text for t in p.iter(f"{{{w_ns}}}t") if t.text]
                    if texts:
                        line = "".join(texts).strip()
                        if line:
                            paragraphs.append(line)
                
                text = "\n\n".join(paragraphs).strip()
                return text if text else "DOCX file contains no readable text."
        except Exception as e:
            return f"Error extracting DOCX text: {e}"

    @classmethod
    def _call_gemini_vision(cls, b64_data: str, mime_type: str) -> str:
        from backend.app.llm.key_pool import key_pool
        models_to_try = ["gemini-flash-lite-latest", "gemini-flash-latest"]
        for _ in range(4):
            key_obj = key_pool.get_next_key(preferred_provider="gemini", strict_provider=True)
            if not key_obj or key_obj.provider != "gemini":
                break
            for model in models_to_try:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key_obj.key_string}"
                    payload = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                                    {
                                        "text": (
                                            "You are an OCR and technical document digitization specialist. "
                                            "Extract all text, sections, bullet points, headers, tables, and code from this document image verbatim. "
                                            "Preserve the original layout, structure, and technical terminology exactly. "
                                            "Do not add conversational preamble. Return only the extracted text."
                                        )
                                    }
                                ]
                            }
                        ],
                        "generationConfig": {"temperature": 0.1}
                    }
                    with httpx.Client(timeout=30.0) as client:
                        resp = client.post(url, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            if "candidates" in data and data["candidates"]:
                                parts = data["candidates"][0].get("content", {}).get("parts", [])
                                if parts and "text" in parts[0]:
                                    return parts[0]["text"].strip()
                        elif resp.status_code == 429:
                            key_obj.trigger_cooldown(30.0)
                            break
                        elif resp.status_code == 401:
                            key_obj.trigger_cooldown(86400.0)
                            break
                except Exception as e:
                    print(f"[DocumentParser] Gemini vision call error with {model}: {e}")
                    continue
        return ""

