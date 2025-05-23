import asyncio
import pytest

pytest.importorskip("docx")
pytest.importorskip("xhtml2pdf")

from app.services.export_service import (
    convert_markdown_to_pdf,
    convert_markdown_to_docx,
    TemplateProcessor,
)


def test_convert_markdown_to_pdf_returns_bytes():
    result = asyncio.run(convert_markdown_to_pdf("# Title\n\nSome content"))
    assert isinstance(result, bytes)
    assert result


def test_convert_markdown_to_docx_returns_bytes():
    result = asyncio.run(convert_markdown_to_docx("# Title\n\nSome content"))
    assert isinstance(result, bytes)
    assert result


def test_template_processor_parse_resume_to_context():
    processor = TemplateProcessor()
    resume = "NAME\nJohn Doe\nEXPERIENCE\nExample Corp\nSKILLS\nPython"
    context = asyncio.run(processor.parse_resume_to_context(resume))
    assert context["name"] == "John Doe"
    assert context["experience"] == "Example Corp"
    assert context["skills"] == "Python"
    assert context["header"] == ""
