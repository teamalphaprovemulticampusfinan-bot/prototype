from typing import List, Literal, Optional
from pydantic import BaseModel

class Report(BaseModel):
    agent: Literal["finance"] = "finance"
    company_name: str
    industry_type: str
    summary: str
    key_thesis: List[str]
    key_risks: List[str]
    warning_note: Optional[str] = None
