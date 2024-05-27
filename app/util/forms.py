import json
import logging
import os
from pathlib import Path
from typing import DefaultDict

logger = logging.getLogger(__name__)


def is_path_allowed(user_path: str, allowed_dir: str) -> bool:
    # Convert to absolute paths
    user_path = Path(user_path).resolve()
    allowed_dir = Path(allowed_dir).resolve()

    try:
        # Check if the user path is within the allowed directory
        user_path.relative_to(allowed_dir)
        return True
    except ValueError:
        return False


class Forms:
    def get_form_body(file="1"):
        form_file = os.path.join(os.getcwd(), "app/forms", f"{file}.json")
        allowed_paths = "app/forms"
        if not is_path_allowed(form_file, allowed_paths):
            logger.error("attempted to access unauthorized paths")
            raise PermissionError("Access to the specified file is not allowed")
        try:
            return json.load(open(form_file, "r"))
        except FileNotFoundError:
            raise FileNotFoundError


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


def apply_fuzzy_parsing(data: dict):
    """
    Converts form data from fuzzy boolean values like, yes, no, 'i promise not' into booleans
    """
    parsed_data = {k: fuzzy_parse_value(v) for k, v in data.items()}
    return parsed_data


def transform_dict(d):
    """
    Turns the nested Models in the format nested_model.key1: "1" into nested_model: {key1: "1", key2: "2" }
    """
    if not any("." in key for key in d):
        return d
    nested_dict = DefaultDict(dict)
    for key, value in d.items():
        parent, child = key.split(".")
        nested_dict[parent][child] = value
    return nested_dict
