# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from app.models.info import InfoModel
from app.models.user import PublicContact
from app.util.authentication import Authentication
from app.util.errors import Errors

logger = logging.getLogger(__name__)


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/infra", tags=["Infra"], responses=Errors.basic_http())


@router.get("/")
async def get_root():
    """
    Get API information.
    """
    return InfoModel(
        name="Onboard Infra",
        description="Infrastructure Management via Onboard.",
        credits=[
            PublicContact(
                first_name="Jonathan",
                surname="Styles",
                ops_email="jstyles@hackucf.org",
            ),
        ],
    )


ERR_VPN_CONFIG_NOT_FOUND = HTTPException(status_code=500, detail="HackUCF OpenVPN Config Not Found")


@router.get("/openvpn")
@Authentication.member
async def download_file(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
):
    """
    An endpoint to Download OpenVPN profile
    """
    # Replace 'path/to/your/file.txt' with the actual path to your file
    file_path = "./HackUCF.ovpn"
    if not Path(file_path).exists():
        ## Return 500 ISE
        logger.error("HackUCF OpenVPN Config Not Found at " + str(Path(file_path).resolve()))
        raise ERR_VPN_CONFIG_NOT_FOUND
    else:
        return FileResponse(file_path, filename="HackUCF.ovpn", media_type="application/octet-stream")
