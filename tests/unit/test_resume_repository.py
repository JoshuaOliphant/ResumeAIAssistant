import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from app.db.session import Base
from app.models.resume import Resume, ResumeVersion
from app.repositories.resume import ResumeRepository
from app.schemas.resume import ResumeVersionCreate


@pytest.fixture()
def in_memory_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_resume_with_versions(session, version_count=1):
    resume = Resume(id=str(uuid.uuid4()), title="Test Resume")
    session.add(resume)
    session.commit()

    for i in range(version_count):
        version = ResumeVersion(
            id=str(uuid.uuid4()),
            resume_id=resume.id,
            content=f"content {i + 1}",
            version_number=i + 1,
        )
        session.add(version)
    session.commit()
    return resume


def test_get_with_current_version(in_memory_session):
    resume = add_resume_with_versions(in_memory_session, version_count=2)
    repo = ResumeRepository(in_memory_session)

    result = repo.get_with_current_version(resume.id)

    assert result.current_version is not None
    assert result.current_version.version_number == 2
    assert result.current_version.content == "content 2"


def test_get_with_all_versions(in_memory_session):
    resume = add_resume_with_versions(in_memory_session, version_count=2)
    repo = ResumeRepository(in_memory_session)

    result = repo.get_with_all_versions(resume.id)

    assert len(result.versions) == 2
    assert [v.version_number for v in result.versions] == [2, 1]


def test_create_version(in_memory_session):
    resume = add_resume_with_versions(in_memory_session, version_count=1)
    repo = ResumeRepository(in_memory_session)

    new_version = repo.create_version(resume.id, ResumeVersionCreate(content="v2"))

    assert new_version.version_number == 2

    updated = repo.get_with_current_version(resume.id)
    assert updated.current_version.id == new_version.id
    assert updated.current_version.version_number == 2

    versions = (
        in_memory_session.query(ResumeVersion)
        .filter_by(resume_id=resume.id)
        .order_by(ResumeVersion.version_number)
        .all()
    )
    assert [v.version_number for v in versions] == [1, 2]
