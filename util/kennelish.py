from typing import Literal
from pydantic import BaseModel

class Kennelish:
    """
    Kennelish (a pun off of GitHub://ZenithDevs/Kennel) is a recursive JSON form renderer.
    It renders JSON as an HTML form. Note that this has NO correlation with Sileo's native
    depiction format, and the similarities were accidential.

    """

    def __init__(self):
        super(Kennelish, self).__init__()


    def parse(obj, user_data=None):
        output = ""
        for entry in obj:
            try:
                if entry['input'] == 'h1':
                    output += Kennelish.header(entry, user_data)
                elif entry['input'] == 'h2':
                    output += Kennelish.header(entry, user_data, "h2")
                elif entry['input'] == 'email':
                    output += Kennelish.text(entry, user_data, "email")
                elif entry['input'] == 'text':
                    output += Kennelish.text(entry, user_data)
                elif entry['input'] == 'radio':
                    output += Kennelish.radio(entry, user_data)
                elif entry['input'] == 'dropdown':
                    output += Kennelish.dropdown(entry, user_data)
                else:
                    output += Kennelish.invalid(entry)
            except Exception as e:
                print(e)
                output += Kennelish.invalid({"input": "Malformed object"})
                continue

        return output

    def label(entry, innerHtml):
        text = f"<h3>{entry.get('label', '')}</h3>"
        text += f"<h4>{entry.get('caption', '')}</h4>"
        return f"<div class='entry'><div>{text}</div><div>{innerHtml}</div></div>"

    def header(entry, user_data=None, tag="h1"):
        output = f"<{tag}>{entry.get('label', '')}</{tag}>"
        output += Kennelish.parse(entry['elements'], user_data)
        return output

    def text(entry, user_data=None, type="text"):
        # Pre-filling of data from database (+ special rule for email discovery)
        if entry.get('prefill'):
            key = entry.get('key', '')
            if key == 'email':
                if user_data.get('email'):
                    prefill = user_data.get('email')
                else:
                    prefill = user_data.get('discord').get('email')
            else:
                prefill = user_data.get(key, '')

            if prefill == None:
                prefill = ""
        else:
            prefill = ""

        # prefill = user_data.get(entry.get('prefill', ''), '')
        output = f"<input type='{type}' value='{prefill}' placeholder='{entry.get('label', '')}' '/>"
        return Kennelish.label(entry, output)

    def radio(entry, user_data=None):
        # Pre-filling of data from database
        if entry.get('prefill'):
            prefill = user_data.get(entry.get('key', ''), '')
        else:
            prefill = ""
        
        
        output = "<fieldset class='radio'>"
        for option in entry['options']:
            selected = "" if option != prefill else "checked"
            output += f"<div><input type='radio' {selected} name='radio_{entry['key']}' id='radio_{entry['key']}_{option}' value='{option}'><label for='radio_{entry['key']}_{option}'>{option}</label></div>"
        output += "</fieldset>"
        return Kennelish.label(entry, output)

    def dropdown(entry, user_data=None):
        # TODO: Pre-filling of data from database
        output = f"<select name='dropdown_{entry['key']}'><option disabled selected value='_default'>Select...</option>"
        for option in entry['options']:
            output += f"<option value='{option}'>{option}</option>"

        if entry.get("other"):
            output += f"<option value='_other'>Other</option></select><input class='other_dropdown' type='text' placeholder='{entry.get('label', 'Other')}...'>"
        else:
            output += "</select>"
        return Kennelish.label(entry, output)

    def invalid(entry):
        return f"<h3 class='invalid'>Invalid Input: {entry['input']}</h3>"


class Transformer:
    """
    Transforms a Kennelish file into a Pydantic model for validation.

    Some terminology to help out:
    - Form: Think of this as the JSON you would send the API.
    - Kennelish: The JSON file that renders the page.
    - Pydantic: A library for strict typing. See: https://pydantic-docs.helpmanual.io/
    """

    def __init__(self):
        super(Transformer, self).__init__()


    def kennelish_to_form(json):
        obj = {}

        for el in json:
            element_type = el.get("input")

            # For if we have an element that contains other elements.
            if element_type == "h1" or element_type == "h2":
                obj = {**obj, **kennelish_to_form(el.get("elements"))}

            # For when a choice is REQUIRED.
            elif element_type == "radio" or (element_type == "dropdown" and el.get("other", False)):
                obj[el.get("key")] = (Literal[tuple(el.get("options"))], None)
            
            # For arbitrary strings.
            else:
                obj[el.get("key")] = (str, None)

        return obj


    def form_to_pydantic(json):
        model = create_model("KennelishGeneratedModel", **json)
        return model


    def kennelish_to_pydantic(json):
        form = kennelish_to_form(json)
        return form_to_pydantic(form)