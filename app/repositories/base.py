from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import uuid4
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder

# Define generic type variables
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for all repositories.
    Provides common CRUD operations that can be inherited by specific repositories.
    """

    def __init__(self, db: Session, model: Type[ModelType]):
        """
        Initialize the repository with a database session and model class.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model

    def get(self, id: str) -> Optional[ModelType]:
        """
        Get an entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            The entity if found, None otherwise
        """
        return self.db.query(self.model).filter(getattr(self.model, "id") == id).first()

    def get_multi(
        self, *, skip: int = 0, limit: int = 100, **filter_args
    ) -> List[ModelType]:
        """
        Get multiple entities with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filter_args: Additional filter arguments
            
        Returns:
            List of entities
        """
        query = self.db.query(self.model)
        for key, value in filter_args.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()

    def create(self, *, obj_in: Union[CreateSchemaType, Dict[str, Any]], user_id: Optional[str] = None) -> ModelType:
        """
        Create a new entity.
        
        Args:
            obj_in: Data to create entity with
            user_id: Optional user ID for entities that belong to users
            
        Returns:
            Created entity
        """
        obj_in_data = obj_in.dict() if isinstance(obj_in, BaseModel) else obj_in
        
        # If the model has a default UUID generation but none is provided, generate one
        if hasattr(self.model, 'id') and 'id' not in obj_in_data:
            obj_in_data['id'] = str(uuid4())
            
        # If user_id is provided and the model has a user_id field, set it
        if user_id and hasattr(self.model, 'user_id'):
            obj_in_data['user_id'] = user_id
            
        db_obj = self.model(**obj_in_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(
        self, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update an entity.
        
        Args:
            db_obj: Entity to update
            obj_in: New data to update with
            
        Returns:
            Updated entity
        """
        obj_data = jsonable_encoder(db_obj)
        update_data = obj_in.dict(exclude_unset=True) if isinstance(obj_in, BaseModel) else obj_in
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, *, id: str) -> Optional[ModelType]:
        """
        Delete an entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Deleted entity or None if not found
        """
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return obj
        return None
