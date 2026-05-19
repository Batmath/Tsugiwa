from fastapi import APIRouter
from ..database import get_db

router = APIRouter(prefix="/ratings", tags=["ratings"])

# Avoir des ratings par manga ! 
