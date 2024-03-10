from typing import Literal

from pydantic import constr, create_model


# Known bug: You cannot pre-fill data stored in second-level DynamoDB levels.
# So "parent.child" won't retrieve a value.
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
                if entry["input"] == "h1":
                    output += Kennelish.header(entry, user_data)
                elif entry["input"] == "h2":
                    output += Kennelish.header(entry, user_data, "h2")
                elif entry["input"] == "h3":
                    output += Kennelish.header(entry, user_data, "h3")
                elif entry["input"] == "p":
                    output += Kennelish.header(entry, user_data, "p")
                elif entry["input"] == "email":
                    output += Kennelish.text(entry, user_data, "email")
                elif entry["input"] == "nid":
                    output += Kennelish.text(entry, user_data, "nid")
                elif entry["input"] == "text":
                    output += Kennelish.text(entry, user_data)
                elif entry["input"] == "radio":
                    output += Kennelish.radio(entry, user_data)
                elif entry["input"] == "checkbox":
                    output += Kennelish.checkbox(entry, user_data)
                elif entry["input"] == "dropdown":
                    output += Kennelish.dropdown(entry, user_data)
                elif entry["input"] == "slider":
                    output += Kennelish.slider(entry, user_data)
                elif entry["input"] == "signature":
                    output += Kennelish.signature(entry, user_data)
                elif entry["input"] == "navigation":
                    output += Kennelish.navigation(entry)
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
        output += Kennelish.parse(entry.get("elements", []), user_data)
        return output

    def signature(entry, user_data=None):
        output = f"<div name='{entry.get('key')}' class='signature'>By submitting this form, you, {user_data.get('first_name', 'HackUCF Member #' + user_data.get('id'))} {user_data.get('surname', '')}, agree to the above terms. This form will be time-stamped.</div>"
        return output

    def text(entry, user_data=None, inp_type="text"):
        # Pre-filling of data from database (+ special rule for email discovery)
        if entry.get("prefill", True):
            key = entry.get("key", "")
            if key == "email":
                if user_data.get("email"):
                    prefill = user_data.get("email")
                else:
                    prefill = user_data.get("discord").get("email")
            else:
                prefill = user_data.get(key, "")

            if prefill is None:
                prefill = ""
        else:
            prefill = ""

        regex_pattern = " "
        if inp_type == "email" and entry.get("domain", False):
            regex_pattern = ' pattern="([A-Za-z0-9.-_+]+)@' + entry.get("domain") + '"'
        elif inp_type == "email":
            regex_pattern = (
                ' pattern="([A-Za-z0-9.-_+]+)@[A-Za-z0-9-]+(.[A-Za-z-]{2,})"'
            )
        elif inp_type == "nid":
            regex_pattern = ' pattern="^([a-z]{2}[0-9]{6})$"'

        output = f"<input class='kennelish_input'{' required' if entry.get('required') else ' '}{regex_pattern} name='{entry.get('key', '')}' type='{'text' if inp_type == 'nid' else inp_type}' value='{prefill}' placeholder='{entry.get('label', '')}' />"
        return Kennelish.label(entry, output)

    def radio(entry, user_data=None):
        # Pre-filling of data from database
        if entry.get("prefill", True):
            prefill = user_data.get(entry.get("key", ""), "")
            if str(prefill) == "True":
                prefill = "Yes"
            elif str(prefill) == "False":
                prefill = "No"
        else:
            prefill = ""

        output = f"<fieldset name='{entry.get('key', '')}'{' required' if entry.get('required') else ' '} class='kennelish_input radio'>"
        for option in entry["options"]:
            selected = "" if option != prefill else "checked"
            output += f"<div><input type='radio' {selected} name='{entry.get('key', '')}' id='radio_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_{option}' value='{option}'><label for='radio_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_{option}'>{option}</label></div>"
        output += "</fieldset>"
        return Kennelish.label(entry, output)

    def checkbox(entry, user_data=None):
        # Checkboxes do not support pre-filling!

        output = f"<fieldset name='{entry.get('key', '')}'{' required' if entry.get('required') else ' '} class='kennelish_input checkbox'>"
        for option in entry.get("options"):
            output += f"<div><input type='checkbox' name='{entry.get('key', '')}' id='checkbox_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_{option}' value='{option}'><label for='checkbox_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_{option}'>{option}</label></div>"

        # Other
        output += f"<div><input type='checkbox' name='{entry.get('key', '')}' id='checkbox_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_OTHER' value='_other'><label for='checkbox_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_OTHER'>Other</label></div>"
        output += f"<input id='{entry.get('key', '').replace('.', '_').replace(' ', '_')}' class='other_checkbox' type='text' placeholder='{entry.get('label', 'Other')}...'>"
        output += "</fieldset>"
        return Kennelish.label(entry, output)

    def dropdown(entry, user_data=None):
        # Pre-filling of data from database
        if entry.get("prefill", True):
            prefill = user_data.get(entry.get("key", ""), "_default")
            if prefill == "":
                prefill = "_default"
        else:
            prefill = "_default"

        output = f"<select class='kennelish_input'{' required' if entry.get('required') else ' '} name='{entry.get('key', '')}'><option disabled {'selected ' if prefill == '_default' else ''}value='_default'>Select...</option>"
        for option in entry.get("options"):
            output += f"<option {'selected ' if prefill == option else ''}value='{option}'>{option}</option>"

        if entry.get("other"):
            output += f"<option value='_other'>Other</option></select><input id='{entry.get('key', '').replace('.', '_').replace(' ', '_')}' class='other_dropdown' type='text' placeholder='{entry.get('label', 'Other')}...'>"
        else:
            output += "</select>"
        return Kennelish.label(entry, output)

    def slider(entry, user_data=None):
        # This is pretty much radio, but modified.

        # Pre-filling of data from database
        if entry.get("prefill", True):
            prefill = user_data.get(entry.get("key", ""), "")
        else:
            prefill = ""

        novice_label = entry.get("novice_label", "Novice")
        expert_label = entry.get("expert_label", "Expert")

        output = f"<span class='caption'>{novice_label}</span><span class='right caption'>{expert_label}</span><br>"
        output += f"<fieldset name='{entry.get('key', '')}'{' required' if entry.get('required') else ' '} class='kennelish_input radio gridded'>"
        for option in range(1, 6):
            selected = "" if option != prefill else "checked"
            output += f"<div><input type='radio' {selected} name='{entry.get('key', '')}' id='radio_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_{option}' value='{option}'><label for='radio_{entry.get('key', '').replace('.', '_').replace(' ', '_')}_{option}'>{option}</label></div>"
        output += "</fieldset>"
        return Kennelish.label(entry, output)

    def navigation(entry):
        if entry.get("prev"):
            # back = f"<a class='btn wide grey' href='{entry.get('prev', '#')}'>{entry.get('prev_label', 'Back')}</a>"
            back = f"<button type='button' class='btn wide grey' onclick='submit_and_nav(\"{entry.get('prev', '#')}\")'>{entry.get('prev_label', 'Back')}</button>"
        else:
            back = ""
        forward = f"<button type='button' class='btn wide' onclick='submit_and_nav(\"{entry.get('next', '#')}\")'>{entry.get('next_label', 'Next')}</button>"
        return f"<div class='entry'><div>{back}</div><div>{forward}</div></div>"

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

    def kwargs_to_str(kwargs):
        print(dir(kwargs))
        for k, v in kwargs.items():
            print(k, v)
            kwargs[k] = str(v)

        return kwargs

    def kennelish_to_form(json):
        obj = {}

        if json is None:
            return {}

        for el in json:
            element_type = el.get("input")

            # For if we have an element that contains other elements.
            if element_type == "h1" or element_type == "h2":
                obj = {**obj, **Transformer.kennelish_to_form(el.get("elements"))}

            # For when a choice is REQUIRED.
            elif element_type == "radio" or (
                element_type == "dropdown" and not el.get("other", True)
            ):
                obj[el.get("key")] = (Literal[tuple(el.get("options"))], None)

            # For emails (specified domain)
            elif element_type == "email" and el.get("domain", False):
                regex_constr = constr(
                    regex="([A-Za-z0-9.-_+]+)@" + el.get("domain").lower()
                )
                obj[el.get("key")] = (regex_constr, None)

            # For emails (any domain)
            elif element_type == "email":
                regex_constr = constr(
                    regex="([A-Za-z0-9.-_+]+)@[A-Za-z0-9-]+(.[A-Za-z-]{2,})"
                )
                obj[el.get("key")] = (regex_constr, None)

            # For NIDs
            elif element_type == "nid":
                regex_constr = constr(regex="(^([a-z]{2}[0-9]{6})$)")
                obj[el.get("key")] = (regex_constr, None)

            # For numbers
            elif element_type == "slider":
                obj[el.get("key")] = (int, None)

            # For arbitrary strings.
            elif el.get("key") is not None:
                obj[el.get("key")] = (str, None)

        return obj

    def form_to_pydantic(json):
        model = create_model("KennelishGeneratedModel", **json)
        return model

    def kennelish_to_pydantic(json):
        form = Transformer.kennelish_to_form(json)
        return Transformer.form_to_pydantic(form)
