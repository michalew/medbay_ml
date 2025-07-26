from decimal import Decimal, InvalidOperation


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
    verbose_name = ""
    field = None
    is_choices = False
    is_function = False
    is_m2m_field = False

    field_list = [x.name for x in obj._meta.fields]
    is_function = key not in field_list

    # Ustaw wartość
    if is_function:
        # Jeśli to funkcja, wywołaj ją i pobierz wynik
        try:
            value = getattr(obj, key)()
        except Exception:
            # Jeśli wywołanie funkcji się nie uda, pobierz atrybut jako string
            value = getattr(obj, key)
    else:
        # Jeśli wartość nie została przekazana, pobierz ją z obiektu
        if value is None:
            value = getattr(obj, key, None)

    try:
        field = obj._meta.get_field(key)
        try:
            is_choices = bool(field.choices)
        except AttributeError:
            pass
        verbose_name = f"{field.verbose_name}"
    except (AttributeError, ValueError, TypeError):
        if is_function:
            # Jeśli funkcja ma short_description, użyj go jako verbose_name
            func = getattr(obj, key, None)
            if func and hasattr(func, "short_description"):
                verbose_name = func.short_description
            else:
                verbose_name = key
        else:
            verbose_name = key

    try:
        if value and field and hasattr(field, "related_model"):
            lookup_value = value.pk if hasattr(value, "pk") else value
            if field.related_model.objects.filter(pk=lookup_value).exists():
                is_m2m_field = True
    except AttributeError:
        pass

    if is_choices:
        try:
            value = getattr(obj, f'get_{field.name}_display')()
        except Exception:
            pass

    # Formatowanie wartości
    try:
        # Zamiana None na pusty string
        value_str = str(value or "").strip()
    except Exception:
        value_str = ""

    # Próba konwersji na Decimal tylko jeśli wartość wygląda na liczbę
    try:
        # Sprawdź, czy wartość jest liczbą lub stringiem reprezentującym liczbę
        if isinstance(value, (int, float, Decimal)):
            dec_value = Decimal(value)
            # Zamień kropkę na przecinek w stringu
            value_str = str(dec_value).replace(".", ",")
        else:
            # Spróbuj skonwertować string na Decimal
            dec_value = Decimal(value_str)
            value_str = str(dec_value).replace(".", ",")
    except (InvalidOperation, ValueError):
        # Jeśli konwersja się nie uda, zostaw oryginalny string
        pass

    if value_str == "":
        value_str = "-----"

    return {
        "verbose_name": verbose_name,
        "field": field,
        "is_choices": is_choices,
        "is_function": is_function,
        "value": value_str,
        "is_m2m_field": is_m2m_field,
    }