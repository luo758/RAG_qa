from __future__ import annotations

from app.services.chunking import split_text
from app.services.parser import extract_text

from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample_docs"


def test_chunking_respects_size_and_overlap():
    text = "第一段。" * 200
    chunks = split_text(text, chunk_size=120, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 125 for chunk in chunks)


def test_markdown_parser():
    assert "产品定位" in extract_text(SAMPLE_DIR / "product-manual.md")


def test_pdf_pptx_and_image_parsers():
    assert "DocFlow" in extract_text(SAMPLE_DIR / "architecture.pdf")
    assert "版本发布" in extract_text(SAMPLE_DIR / "release-notes.pptx")
    assert "测试 OCR" in extract_text(SAMPLE_DIR / "troubleshooting.png")
