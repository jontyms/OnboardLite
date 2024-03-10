from typing import List, Optional

from pydantic import BaseModel

# Import data types
from models.user import PublicContact


class InfoModel(BaseModel):
    name: Optional[str] = "Onboard"
    description: Optional[str] = None
    credits: List[PublicContact]
