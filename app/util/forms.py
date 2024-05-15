import json
import os

from pydantic import ValidationError


class Forms:
    def get_form_body(file="1"):
        # if file.contains("..", "\\"):
        #    raise ValueError("Invalid file name")
        try:
            form_file = os.path.join(os.getcwd(), "forms", f"{file}.json")
            return json.load(open(form_file, "r"))
        except FileNotFoundError:
            raise


def fuzzy_parse_value(value):
    # Convert common boolean-like values
    if isinstance(value, str):
        value_test = value.lower()
        if value_test in {"yes", "true", "1", "Yes"}:
            return True
        if value_test in {"no", "false", "0", "No"}:
            return False
        if "i promise not" in value_test:
            return True

    # Convert other types as needed

    return value


def apply_fuzzy_parsing(data: dict, model_class):
    parsed_data = {k: fuzzy_parse_value(v) for k, v in data.items()}
    try:
        validated_data = model_class(**parsed_data)
    except ValidationError as e:
        raise Exception(
            status_code=422,
            detail={"description": "Malformed input.", "errors": e.errors()},
        )
    return validated_data