from unittest.mock import patch

from app.services.diff_service import DiffGenerator


def test_diff_generator_html_view_uses_helper():
    with patch("app.services.diff_service.generate_diff_html_document") as mock_doc:
        mock_doc.return_value = "<html>diff</html>"
        gen = DiffGenerator()
        result = gen.html_diff_view("A", "B")
        mock_doc.assert_called_once_with("A", "B")
        assert result == "<html>diff</html>"


