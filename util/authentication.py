import time

from functools import wraps
from jose import JWTError, jwt
from typing import Optional

from fastapi import Request

# Import options and errors
from util.errors import Errors
from util.options import Options
options = Options.fetch()

class Authentication:
    def __init__(self):
        super(Authentication, self).__init__

    def admin(func):
        @wraps(func)
        async def wrapper(request: Request, token: Optional[str], *args, **kwargs):

            # Validate auth.
            if not token:
                return Errors.generate(request, 401, "You are not logged in.")

            try:
                payload = jwt.decode(token, options.get("jwt").get("secret"), algorithms=options.get("jwt").get("algorithm"))
                is_admin: bool = payload.get("sudo", False)
                creation_date: float = payload.get("issued", -1)
            except Exception:
                return Errors.generate(request, 403, "Invalid token provided. Please log in again and try again.")

            if not is_admin:
                return Errors.generate(request, 403, "You are not a sudoer.", essay="If you think this is an error, please try logging in again.")

            if time.time() > creation_date + options.get("jwt").get("lifetime").get("sudo"):
                return Errors.generate(
                    request, 403, "Session not new enough to verify sudo status.",
                    essay="Unlike normal log-in, non-bot sudoer sessions only last a day. This is to ensure the security of Hack@UCF member PII. "
                    "Simply re-log into Onboard to continue."
                )

            return await func(request, token, *args, **kwargs)

        return wrapper


    def member(func):
        @wraps(func)
        async def wrapper_member(request: Request, token: Optional[str], payload: Optional[object], *args, **kwargs):

            # Validate auth.
            if not token:
                return Errors.generate(request, 401, "You are not logged in.")

            try:
                payload = jwt.decode(token, options.get("jwt").get("secret"), algorithms=options.get("jwt").get("algorithm"))
                creation_date: float = payload.get("issued", -1)
            except Exception:
                return Errors.generate(request, 403, "Invalid token provided. Please log in again and try again.")

            if time.time() > creation_date + options.get("jwt").get("lifetime").get("user"):
                return Errors.generate(
                    request, 403, "Session expired.",
                    essay="Sessions last for about fifteen weeks. You need to re-log-in between semesters."
                )

            return await func(request, token, payload, *args, **kwargs)

        return wrapper_member