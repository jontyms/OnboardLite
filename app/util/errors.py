from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


class Errors:
    def __init__(self):
        super(Errors, self).__init__

    def generate(
        request,
        num=404,
        msg="Page not found.",
        essay="",
        return_url="/",
        return_text="Return to home",
    ):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "code": num,
                "reason": msg,
                "essay": essay,
                "return_url": return_url,
                "return_text": return_text,
            },
            status_code=num,
        )

    def basic_http():
        return {
            404: {"description": "Page not found"},
            401: {"description": "User not authorized. Try logging in?"},
            403: {"description": "User does not have access to this page."},
        }
