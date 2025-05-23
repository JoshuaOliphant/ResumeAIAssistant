import pytest
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.repositories.base import BaseRepository

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def repo(db_session: Session) -> BaseRepository:
    return BaseRepository(db_session, Item)


def test_create_and_get(repo: BaseRepository) -> None:
    obj = repo.create(obj_in={"name": "Alice"})
    fetched = repo.get(obj.id)
    assert fetched is not None
    assert fetched.id == obj.id
    assert fetched.name == "Alice"


def test_get_multi(repo: BaseRepository) -> None:
    item_a = repo.create(obj_in={"name": "A"})
    item_b = repo.create(obj_in={"name": "B"})

    all_items = repo.get_multi()
    assert len(all_items) == 2
    assert {item.name for item in all_items} == {"A", "B"}

    filtered = repo.get_multi(name="A")
    assert len(filtered) == 1
    assert filtered[0].name == "A"


def test_update(repo: BaseRepository) -> None:
    obj = repo.create(obj_in={"name": "Old"})
    updated = repo.update(db_obj=obj, obj_in={"name": "New"})

    assert updated.name == "New"
    fetched = repo.get(obj.id)
    assert fetched is not None and fetched.name == "New"


def test_delete(repo: BaseRepository) -> None:
    obj = repo.create(obj_in={"name": "Delete"})
    repo.delete(id=obj.id)
    assert repo.get(obj.id) is None
