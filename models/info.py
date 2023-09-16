from pydantic import BaseModel
from typing import Optional, List

# Import data types
from models.user import PublicContact


class InfoModel(BaseModel):
    name: Optional[str] = "Onboard"
    description: Optional[str] = None
    credits: List[PublicContact]
