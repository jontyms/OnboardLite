from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


class Errors:
    def __init__(self):
        super(Errors, self).__init__

    def generate(request, num=404, msg="Page not found.", essay=""):
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "code": num, "reason": msg, "essay": essay},
            status_code=num,
        )

    def basic_http():
        return {
            404: {"description": "Page not found"},
            401: {"description": "User not authorized. Try logging in?"},
            403: {"description": "User does not have access to this page."},
        }
