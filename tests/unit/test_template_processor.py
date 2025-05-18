import io
import os
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from app.services.export_service import TemplateProcessor


@pytest.mark.asyncio
async def test_parse_resume_to_context(sample_resume):
    processor = TemplateProcessor()
    context = await processor.parse_resume_to_context(sample_resume)
    assert "experience" in context
    assert "skills" in context


@pytest.mark.asyncio
async def test_get_template_not_found():
    processor = TemplateProcessor(templates_dir="not_real")
    with pytest.raises(ValueError):
        await processor.get_template("missing")


@pytest.mark.asyncio
async def test_apply_template_calls_docxtpl(sample_resume):
    with TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "tmpl.docx")
        # create empty file to satisfy existence check
        with open(path, "wb") as f:
            f.write(b"fake")

        processor = TemplateProcessor(templates_dir=tmpdir)
        with patch("app.services.export_service.DocxTemplate") as MockDoc:
            doc_instance = MagicMock()
            MockDoc.return_value = doc_instance
            doc_instance.save.side_effect = lambda buf: buf.write(b"data")

            result = await processor.apply_template("tmpl", {"section": "text"})

            MockDoc.assert_called_once_with(path)
            doc_instance.render.assert_called_once()
            assert isinstance(result, io.BytesIO)
            assert result.getvalue() == b"data"
