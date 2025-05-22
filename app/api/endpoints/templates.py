"""
API endpoints for resume templates
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from pydantic import BaseModel

class Template(BaseModel):
    id: str
    name: str
    description: str
    preview_url: str

router = APIRouter()

# Simple placeholder templates for now
default_templates = [
    Template(
        id=str(uuid.uuid4()),
        name="Modern Template",
        description="A modern, clean template with a professional look",
        preview_url="/templates/modern.png"
    ),
    Template(
        id=str(uuid.uuid4()),
        name="Traditional Template",
        description="A traditional layout suitable for most industries",
        preview_url="/templates/traditional.png"
    ),
]

@router.get("/", response_model=List[Template])
async def get_templates():
    """
    Get list of available resume templates.
    """
    return default_templates