import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.job import JobDescription
from app.repositories.job import JobRepository


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite session for repository tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_from_url(db_session):
    repo = JobRepository(db_session)
    data = {
        "id": "job1",
        "title": "Engineer",
        "company": "Acme",
        "description": "Build things",
        "url": "https://example.com/job",
    }

    created = repo.create_from_url(data, user_id="user123")

    assert created.id == "job1"
    assert created.title == "Engineer"
    assert created.company == "Acme"
    assert created.description == "Build things"
    assert created.source_url == "https://example.com/job"
    assert created.is_from_url is True
    assert created.user_id == "user123"

    fetched = db_session.get(JobDescription, "job1")
    assert fetched is not None
    assert fetched.title == "Engineer"


def test_check_user_access_public_job():
    repo = JobRepository(MagicMock())
    job = MagicMock(spec=JobDescription)
    job.user_id = None
    repo.get = MagicMock(return_value=job)

    assert repo.check_user_access("job1", "any") is True
    repo.get.assert_called_once_with("job1")


def test_check_user_access_owned_job():
    repo = JobRepository(MagicMock())
    job = MagicMock(spec=JobDescription)
    job.user_id = "owner"
    repo.get = MagicMock(return_value=job)

    assert repo.check_user_access("job1", "owner") is True


def test_check_user_access_other_user_denied():
    repo = JobRepository(MagicMock())
    job = MagicMock(spec=JobDescription)
    job.user_id = "owner"
    repo.get = MagicMock(return_value=job)

    assert repo.check_user_access("job1", "not_owner") is False


def test_check_user_access_job_not_found():
    repo = JobRepository(MagicMock())
    repo.get = MagicMock(return_value=None)

    assert repo.check_user_access("job1", "user") is False
