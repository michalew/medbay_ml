from django.core.exceptions import ObjectDoesNotExist
from .logic import get_field_properties, check_if_field_is_history
from simple_history.models import HistoricalRecords, registered_models, apps



def get_diff(self):
    diff = []

    # Ignorowane klucze - domyślne oraz użytkownika
    ignored_keys = ["history_id", "history_date", "history_user_id", "date", "history_type", "_state"]
    custom_keys = getattr(self.history_object, 'ignored_keys', [])
    ignored_keys += custom_keys

    # Pobranie aktualnego słownika obiektu
    dict1 = self.__dict__
    try:
        history2 = self.get_previous_by_history_date()
        while history2.history_object.pk != self.history_object.pk:
            history2 = history2.get_previous_by_history_date()
        dict2 = history2.__dict__
    except ObjectDoesNotExist:
        dict2 = {}

    if not dict2:
        diff.append("Utworzono obiekt.")

    # Pobranie oryginalnego obiektu
    org_object = getattr(self, 'history_object', self)

    # Iteracja po wspólnych kluczach
    keys = set(dict1.keys()).intersection(dict2.keys())
    for key in keys:
        if key in ignored_keys or dict1[key] == dict2[key]:
            continue

        # Rozwiązanie problemu kluczy `_id` (relacje)
        if key.endswith("_id"):
            key = key[:-3]

        # Pobierz szczegóły pola dla każdej instancji
        try:
            field_old, field_cur, field_org = (
                get_field_properties(obj, key, getattr(obj, key, None)) for obj in (history2, self, org_object)
            )
            verbose_name = field_org.get('verbose_name', key)
        except Exception:
            verbose_name = key

        # Obsługa historii pól z relacjami
        field_his = check_if_field_is_history(org_object, key)
        if field_his.get('is_history', False):
            model_path = field_his.get('model_path')
            try:
                rel_model = apps.get_model(
                    app_label=model_path.split('.')[0],
                    model_name=model_path.split('.')[2]
                )
                value_old = [int(x) for x in dict2.get(key, "").split(",") if x]
                value_cur = [int(x) for x in dict1.get(key, "").split(",") if x]
                removed = [x for x in value_old if x not in value_cur]
                added = [x for x in value_cur if x not in value_old]

                # Dodawanie zmian w relacjach
                for change, action in [(removed, "usunięto"), (added, "dodano")]:
                    if change:
                        diff.append(f"{verbose_name}: {action} powiązania:")
                        for obj_id in change:
                            related_obj = rel_model.objects.filter(pk=obj_id).first()
                            obj_repr = str(related_obj) if related_obj else f"[#{obj_id}]"
                            diff.append(f" - {obj_repr}")
            except (ObjectDoesNotExist, LookupError):
                pass
        else:
            # Obsługa zwykłych atrybutów
            diff.append(f"{verbose_name}: zmiana z '{dict2.get(key)}' na '{dict1.get(key)}'")

    return diff


"""
class DiffedHistoricalRecords(HistoricalRecords):
    def create_history_model(self, model, inherited=None):

        #Creates a historical model to associate with the provided model.
        attrs = {'__module__': self.module}

        try:
            app_config = apps.get_app_config(model._meta.app_label)
            app_label = app_config.label
        except LookupError:
            app_label = model._meta.app_label

        if model.__module__ != self.module:
            attrs['__module__'] = self.module
        else:
            attrs['__module__'] = '%s.models' % app_label

        fields = self.copy_fields(model)
        attrs.update(fields)
        attrs.update(self.get_extra_fields(model, fields))

        class Meta:
            pass

        meta_options = self.get_meta_options(model)
        for key, value in meta_options.items():
            setattr(Meta, key, value)

        if self.table_name is not None:
            Meta.db_table = self.table_name

        attrs['Meta'] = Meta
        attrs['diff'] = get_diff

        name = 'Historical%s' % model._meta.object_name
        registered_models[model._meta.db_table] = model
        return type(name, self.bases, attrs)
"""


class DiffedHistoricalRecords(HistoricalRecords):
    def create_history_model(self, model, inherited=None):
        # Wywołanie oryginalnej metody z klasy bazowej
        history_model = super().create_history_model(model, inherited)

        # Dodanie własnej logiki
        history_model.add_to_class('diff', get_diff)

        return history_model
