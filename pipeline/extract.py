import base64
import io
import json
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from xml.etree import ElementTree

import anthropic
from PIL import Image
from rich.console import Console

console = Console()

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=60.0)
    return _client


def _encode_pil(img: Image.Image) -> Tuple[str, str]:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8"), "image/png"


def _encode_file(path: Path) -> Tuple[str, str]:
    media_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    media_type = media_map.get(path.suffix.lower(), "image/jpeg")
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8"), media_type


_EXTRACTION_PROMPT = """\
You are analysing conference presentation material (a slide or page from a deck).

Conference: {conference}
Speaker: {speaker}

Extract ALL of the following from this content:
1. Main topic or title
2. Key points and insights (each as a separate item)
3. Statistics, data points, or numbers — include the full number and context
4. Direct quotes or speaker statements
5. Frameworks, models, methodologies, or named concepts shown
6. Technologies, products, or company names mentioned
7. HOT TAKES: anything counterintuitive, controversial, or that challenges conventional wisdom — explain why it's surprising

Return ONLY valid JSON with exactly these keys:
{{
  "title": "string",
  "key_points": ["string"],
  "data_points": ["string — include the number and full context"],
  "quotes": ["string"],
  "frameworks": ["string"],
  "technologies": ["string"],
  "hot_takes": ["string — state the claim and why it's counterintuitive"],
  "raw_text": "string — all visible text verbatim"
}}

If a field has no content, use an empty list or empty string. Do not include any text outside the JSON.\
"""

_TEXT_EXTRACTION_PROMPT = """\
Extract structured insights from this slide/page text.

Conference: {conference}
Speaker: {speaker}

TEXT:
{text}

Return ONLY valid JSON:
{{
  "title": "",
  "key_points": [],
  "data_points": [],
  "quotes": [],
  "frameworks": [],
  "technologies": [],
  "hot_takes": [],
  "raw_text": ""
}}\
"""


def _parse_json_response(text: str) -> Dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {
        "title": "",
        "key_points": [text],
        "data_points": [],
        "quotes": [],
        "frameworks": [],
        "technologies": [],
        "hot_takes": [],
        "raw_text": text,
    }


def _extract_via_vision(b64_data: str, media_type: str, context: Dict) -> Dict:
    prompt = _EXTRACTION_PROMPT.format(
        conference=context.get("conference_name", "Unknown"),
        speaker=context.get("speaker", "Unknown"),
    )
    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return _parse_json_response(response.content[0].text)


def _extract_via_text(text: str, context: Dict) -> Dict:
    prompt = _TEXT_EXTRACTION_PROMPT.format(
        conference=context.get("conference_name", "Unknown"),
        speaker=context.get("speaker", "Unknown"),
        text=text[:4000],
    )
    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json_response(response.content[0].text)


def _dedupe_list(lst: list) -> list:
    seen = set()
    result = []
    for item in lst:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


_MAX_IMAGE_BYTES = int(5 * 1024 * 1024 * 3 / 4) - 65536  # API measures base64 size; raw limit ≈ 3.69 MB


def _encode_file_resized(path: Path) -> Tuple[str, str]:
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) <= _MAX_IMAGE_BYTES:
        media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        media_type = media_map.get(path.suffix.lower(), "image/jpeg")
        return base64.standard_b64encode(raw).decode("utf-8"), media_type
    img = Image.open(path).convert("RGB")
    quality = 85
    scale = 1.0
    while True:
        w, h = int(img.width * scale), int(img.height * scale)
        resized = img.resize((w, h), Image.LANCZOS) if scale < 1.0 else img
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= _MAX_IMAGE_BYTES:
            return base64.standard_b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"
        if quality > 60:
            quality -= 10
        else:
            scale *= 0.8


def _extract_image_file(path: Path, context: Dict) -> Dict:
    b64, media_type = _encode_file_resized(path)
    result = _extract_via_vision(b64, media_type, context)
    result["source_file"] = str(path)
    result["source_type"] = "image"
    return result


def _extract_text_file(path: Path, context: Dict) -> Dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    return _extract_private_safe_text(path, text, context, "text")


def _extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in root.findall(".//w:p", ns):
        parts = [node.text or "" for node in para.findall(".//w:t", ns)]
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def _extract_docx_file(path: Path, context: Dict) -> Dict:
    text = _extract_docx_text(path)
    return _extract_private_safe_text(path, text, context, "docx")


def _extract_private_safe_text(path: Path, text: str, context: Dict, source_type: str) -> Dict:
    if context.get("privacy_mode"):
        from pipeline.privacy import anonymize_text
        text = anonymize_text(text, strict=True)
    result = _extract_via_text(text, context)
    result["source_file"] = str(path)
    result["source_type"] = source_type
    return result


def _extract_pdf(path: Path, context: Dict) -> Dict:
    max_pages = context.get("max_pages_per_pdf", 30)

    if context.get("privacy_mode"):
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                text = "\n\n".join((p.extract_text() or "") for p in pdf.pages[:max_pages])
        except Exception as e:
            raise RuntimeError(f"Privacy-mode PDF text extraction failed: {e}") from e
        return _extract_private_safe_text(path, text, context, "pdf")

    try:
        from pdf2image import convert_from_path
        pil_images = convert_from_path(str(path), dpi=150, fmt="PNG")
    except Exception as e:
        console.print(f"  [yellow]pdf2image failed ({e}). Falling back to text.[/yellow]")
        pil_images = []

    text_pages: list = []
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            text_pages = [p.extract_text() or "" for p in pdf.pages]
    except Exception:
        pass

    total = min(max(len(pil_images), len(text_pages)), max_pages)
    if total == 0:
        return {"source_file": str(path), "source_type": "pdf", "page_count": 0}

    all_pages = []
    for i in range(total):
        console.print(f"    page {i + 1}/{total}", end="\r")
        page_ctx = {**context, "page_number": i + 1}

        try:
            if i < len(pil_images):
                b64, mt = _encode_pil(pil_images[i])
                page_data = _extract_via_vision(b64, mt, page_ctx)
            elif i < len(text_pages) and text_pages[i].strip():
                page_data = _extract_via_text(text_pages[i], page_ctx)
            else:
                continue
        except Exception as e:
            console.print(f"\n  [yellow]Skipped page {i + 1}: {e}[/yellow]")
            continue

        page_data["page"] = i + 1
        all_pages.append(page_data)

    console.print()

    return {
        "source_file": str(path),
        "source_type": "pdf",
        "page_count": len(all_pages),
        "pages": all_pages,
        "title": next((p.get("title", "") for p in all_pages if p.get("title")), path.stem),
        "key_points": _dedupe_list([pt for p in all_pages for pt in p.get("key_points", [])]),
        "data_points": _dedupe_list([pt for p in all_pages for pt in p.get("data_points", [])]),
        "quotes": _dedupe_list([pt for p in all_pages for pt in p.get("quotes", [])]),
        "frameworks": _dedupe_list([pt for p in all_pages for pt in p.get("frameworks", [])]),
        "technologies": _dedupe_list([pt for p in all_pages for pt in p.get("technologies", [])]),
        "hot_takes": _dedupe_list([pt for p in all_pages for pt in p.get("hot_takes", [])]),
    }


def extract_artifact(path: Path, context: Dict) -> Optional[Dict]:
    suffix = path.suffix.lower()
    console.print(f"  Extracting [cyan]{path.name}[/cyan]...")

    if suffix == ".pdf":
        return _extract_pdf(path, context)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return _extract_image_file(path, context)
    if suffix in {".txt", ".md"}:
        return _extract_text_file(path, context)
    if suffix == ".docx":
        return _extract_docx_file(path, context)

    console.print(f"  [yellow]Unsupported: {suffix}[/yellow]")
    return None
