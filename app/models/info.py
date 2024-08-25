# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
from typing import List, Optional

from pydantic import BaseModel

# Import data types
from app.models.user import PublicContact


class InfoModel(BaseModel):
    name: Optional[str] = "Onboard"
    description: Optional[str] = None
    credits: List[PublicContact]
