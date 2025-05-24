from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch

with patch("fastapi.templating.Jinja2Templates") as _templates:
    _templates.return_value = object()
    from app.api.api import app
    from app.api.endpoints import resumes


def test_resume_diff_endpoint_generates_html():
    diff_html = "<div>diff</div>"

    class DummyResume:
        id = "res1"
        title = "R"
        user_id = None
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()

    class DummyVersion:
        def __init__(self, vid, content):
            self.id = vid
            self.resume_id = "res1"
            self.content = content
            self.version_number = 1
            self.created_at = datetime.utcnow()
            self._is_customized = 0

        @property
        def is_customized(self):
            return bool(self._is_customized)

    version_a = DummyVersion("v1", "old")
    version_b = DummyVersion("v2", "new")

    class QueryResume:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyResume()

    class QueryA:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return version_a

    class QueryB:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return version_b

    class DummySession:
        def __init__(self):
            self.calls = 0

        def query(self, model):
            self.calls += 1
            if self.calls == 1:
                return QueryResume()
            if self.calls == 2:
                return QueryA()
            return QueryB()

    def override_db():
        yield DummySession()

    def override_user():
        return None

    app.dependency_overrides[resumes.get_db] = override_db
    app.dependency_overrides[resumes.get_optional_current_user] = override_user

    with patch.object(resumes, "DiffGenerator") as mock_gen:
        mock_gen.return_value.html_diff_view.return_value = diff_html
        client = TestClient(app)
        resp = client.get(
            "/api/v1/resumes/res1/diff",
            params={"source_version_id": "v1", "target_version_id": "v2"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"diff_html": diff_html}
        mock_gen.return_value.html_diff_view.assert_called_once_with("old", "new")

    app.dependency_overrides = {}
