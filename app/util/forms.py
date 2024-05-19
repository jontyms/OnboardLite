import json
import logging
import os
from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)

class Forms:
    def get_form_body(file="1"):
        # if file.contains("..", "\\"):
        #    raise ValueError("Invalid file name")
        try:
            form_file = os.path.join(os.getcwd(), "app/forms", f"{file}.json")
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


def apply_fuzzy_parsing(data: dict):
    parsed_data = {k: fuzzy_parse_value(v) for k, v in data.items()}
    return parsed_data


def parse_dict_to_model(model_class, data: Dict[str, Any]):
    model_data = {}
    nested_data = {}

    # Separate nested and non-nested fields
    for key, value in data.items():
        if '.' in key:
            nested_model, nested_field = key.split('.', 1)
            if nested_model not in nested_data:
                nested_data[nested_model] = {}
            nested_data[nested_model][nested_field] = value
        else:
            model_data[key] = value

    # Instantiate the main model
    model_instance = model_class(**model_data)

    # Recursively parse nested models
    # Recursively parse nested models
    for nested_model, nested_fields in nested_data.items():
        nested_model_class = getattr(model_class, nested_model).property.mapper.class_
        nested_instance = parse_dict_to_model(nested_model_class, nested_fields)
        setattr(model_instance, nested_model, nested_instance)

    return model_instance

def update_model_instance(instance, data):
    for key, value in data.items():
        if value is not None:
            attr = getattr(instance, key)

            if isinstance(attr, SQLModel):
                # If the attribute is a nested model, recursively update it
                update_model_instance(attr, value)
                logger.info("Nested   " + str(attr) + "   value  " +  str(value))
            else:
                # Otherwise, update the attribute directly
                setattr(instance, key, value)
                logger.info("regular   " + str(attr) + "  value  " + str(value))
