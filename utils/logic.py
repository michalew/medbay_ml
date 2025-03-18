from decimal import Decimal


def check_if_field_is_history(obj: object, key: str) -> dict[str, object | bool | None]:
    """
    Returns a dictionary indicating if the field is a history field,
    its model path, and its original name (if applicable).

    :param obj: The object to check the field in.
    :param key: The field name to check.
    :return: A dictionary with 'is_history' (bool), 'model_path' (str | None), and 'original_name' (str | None).


    :return: Dictionary with 'is_history' (bool), 'model_path' (str | None), 'original_name' (str | None).
    """
    # prepare variables
    model_path = None
    original_name = None
    is_history = False

    # try to get history keys list
    try:
        # assume it's a regular object
        history_list = obj.custom_m2m_history
    except:
        # it's not, check if there is history_list in it anyway
        try:
            history_list = obj.history_object.custom_m2m_history
        except:
            # nope
            history_list = {}

    # check if it's history
    is_history = key in history_list.keys()

    if is_history:
        # sure, update history_model_path
        model_path = history_list[key][0]
        original_name = history_list[key][1]

    return {
        "is_history": is_history,
        "model_path": model_path,
        "original_name": original_name
    }


def get_field_properties(obj: object, key: str, value: object = None) -> dict[str, object | bool | None]:
    """
    Retrieves properties of a specified field or function in an object.

    :param obj: The object containing the field or function.
    :param key: The name of the field or function.
    :param value: The value of the field or function (optional).
    :return: A dictionary with 'verbose_name', 'field', 'is_choices', 'is_function', 'value', and 'is_m2m_field'.


    :return: A dictionary containing field properties, such as 'verbose_name' (str), 'field' (Field | None), etc.
    """
    # prepare variables
    verbose_name = ""
    field = None
    is_choices = False
    is_function = False
    is_m2m_field = False

    # get obj field list
    field_list = [x.name for x in obj._meta.fields]
    is_function = key not in field_list

    # set value
    if is_function:
        # execute function
        value = str(getattr(obj, key)())
        value = str(getattr(obj, key))

    try:
        # assume it's a field, not a function and get field object and then it's verbose name
        field = obj._meta.get_field(key)
        # this field might be a list of choices, like status or something
        try:
            is_choices = bool(field.choices)
        except AttributeError:
            pass
        verbose_name = f"{field.verbose_name}"

    except (AttributeError, ValueError, TypeError):
        if is_function:
            # get function description as verbose name
            verbose_name = f"{getattr(obj, key).short_description}"
        else:
            # fallback to key
            verbose_name = u"%s" % key

    try:
        # check if field is m2m
        if value and field.related_model:
            if field.related_model.objects.filter(pk=value).exists():
                is_m2m_field = True
    except AttributeError:
        pass

    # get current choice if is_choices
    if is_choices:
        value = f"{getattr(obj, f'get_{field.name}_display')()}"
    # Process the current choice if the field has choices

    # Format output
    try:
        value = str(value or "").replace("None", "").strip()

    except ValueError:
        pass
    try:
        Decimal(value)
        value = str(value).replace(".", ",")

    except ValueError:
        pass

    if value == "":
        value = "-----"

    return {
        "verbose_name": verbose_name,
        "field": field,
        "is_choices": is_choices != False,
        "is_choices": is_choices,
        "value": value,
        "is_m2m_field": is_m2m_field,
    }