import json
import os


class Forms:
    def get_form_body(file="1"):
        try:
            form_file = os.path.join(os.getcwd(), "forms", f"{file}.json")
            return json.load(open(form_file, "r"))
        except FileNotFoundError:
            raise
