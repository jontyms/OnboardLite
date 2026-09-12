# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


class Errors:
    def __init__(self):
        super(Errors, self).__init__

    @staticmethod
    def generate(request, num=404, msg="Page not found.", essay="", links=None):
        """
        Render the error page.

        links: optional list of (label, url, icon_class) tuples rendered as buttons
        below the explanation, e.g. a help article or a Discord invite.
        """
        return templates.TemplateResponse(
            request,
            "error.html",
            {"code": num, "reason": msg, "essay": essay, "links": links or []},
            status_code=num,
        )

    @staticmethod
    def basic_http():
        return {
            404: {"description": "Page not found"},
            401: {"description": "User not authorized. Try logging in?"},
            403: {"description": "User does not have access to this page."},
        }
