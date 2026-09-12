from fastapi import APIRouter
from app.services.analysis import analyse_report

router = APIRouter(prefix="/analyse", tags=["analyse"])

@router.post("/")
def analyse(raw_text: str, language: str = "english"):
    """
    Standalone analysis endpoint — takes report text, returns risk assessment.
    Internally uses the same logic as report creation, so results are consistent.
    """
    result = analyse_report(raw_text)
    return {
        "raw_text": raw_text,
        "language": language,
        **result,
    }