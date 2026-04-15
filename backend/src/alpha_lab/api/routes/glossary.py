"""Glossary API routes。

GET /api/glossary          → 回全部術語（key → GlossaryTerm）
GET /api/glossary/{term_key}   → 回單一術語
"""

from fastapi import APIRouter, HTTPException

from alpha_lab.glossary.loader import get_term, load_terms
from alpha_lab.schemas.glossary import GlossaryTerm

router = APIRouter(tags=["glossary"])


@router.get("/glossary", response_model=dict[str, GlossaryTerm])
async def list_glossary_terms() -> dict[str, GlossaryTerm]:
    return load_terms()


@router.get("/glossary/{term_key}", response_model=GlossaryTerm)
async def get_glossary_term(term_key: str) -> GlossaryTerm:
    term = get_term(term_key)
    if term is None:
        raise HTTPException(status_code=404, detail=f"term {term_key} not found")
    return term
