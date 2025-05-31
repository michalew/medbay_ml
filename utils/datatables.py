# -*- coding: utf-8 -*-
import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q, Value, F, QuerySet
from django.db.models.functions import Concat
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.utils.cache import add_never_cache_headers
from django.contrib.auth import get_user_model

User = get_user_model()


def parse_value(obj: Any, column_name: str) -> Any:
    """
    Given attribute name and object, attempts to get the value,
    execute it if it's a method and parse it
    """
    value: Any = ""
    if isinstance(obj, dict):
        value = obj.get(column_name, "")
    else:
        value = getattr(obj, column_name, "")

    if callable(value):
        value = value()

    if (isinstance(value, str) or not value) and "date" in column_name:
        try:
            return datetime.datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            return datetime.date(datetime.MINYEAR, 1, 1)
    return value


def order_by_generated_fields(
    data: Union[QuerySet, List[Any]],
    columns: List[Tuple[str, bool]]
) -> Union[QuerySet, List[Any]]:
    for column in columns:
        name, desc = column
        data = sorted(data, key=lambda a: parse_value(a, name), reverse=desc)
    return data


def order_queryset(
    queryset: QuerySet,
    sorting_cols: List[Dict[str, Union[str, bool]]]
) -> Union[QuerySet, List[Any]]:
    """
    Takes request data and data to sort.

    Returns sorted data and columns which couldn't be used
    """
    unused_columns: List[Tuple[str, bool]] = []
    model_sorting_cols: List[str] = []

    for col in sorting_cols:
        prefix = "-" if not col["ascending"] else ""
        org_col = col["name"].split("__")[0]

        try:
            queryset.model._meta.get_field(org_col)
            model_sorting_cols.append(f"{prefix}{org_col}")
        except FieldDoesNotExist:
            if org_col in getattr(queryset.query, "annotations", {}):
                model_sorting_cols.append(f"{prefix}{org_col}")
            else:
                unused_columns.append((org_col, prefix != "-"))

    return order_by_generated_fields(
        queryset.order_by(*model_sorting_cols), unused_columns
    )


def add_filter(this_filter: Optional[Q], new_filter: Q, optional: bool = False) -> Q:
    """
    Extends given filter with given parameters.

    Params:
    this_filter: filter to which we're adding another filter
    new_filter: filter we're adding
    optional: whether we should use AND or OR operation
    """
    if not this_filter:
        return new_filter
    if optional:
        return this_filter | new_filter
    return this_filter & new_filter


def user_name_annotation(field_name: str) -> Any:
    """
    Returns a field definition for queryset annotation so we could filter by
    full name without stupid hacks
    """
    return Concat(
        F(f"{field_name}__first_name"),
        Value(' '),
        F(f"{field_name}__last_name")
    )


def filter_queryset(
    objects: QuerySet,
    searchable_columns: Dict[str, str],
    column_index_name_map: Dict[str, str],
    global_query: Optional[str] = None
) -> QuerySet:
    current_filter: Optional[Q] = None
    annotations = getattr(objects.query, "annotations", {}).keys()

    for column, query in searchable_columns.items():
        if global_query:
            query = global_query

        if not query:
            continue

        db_column = column_index_name_map.get(column, column)

        field = None
        try:
            field = objects.model._meta.get_field(db_column)
        except FieldDoesNotExist:
            if "__" in db_column or db_column in annotations:
                current_filter = add_filter(
                    current_filter,
                    Q(**{f"{db_column}__icontains": query}),
                    optional=global_query is not None
                )
            continue

        related_model = getattr(field, "related", None)
        m2m = getattr(field, "m2m_db_table", None)
        choices = getattr(field, "choices", None)

        if related_model:
            if not m2m:
                current_filter = add_filter(
                    current_filter,
                    Q(**{f"{db_column}__name__icontains": query}),
                    optional=global_query is not None
                )
        elif choices:
            in_choices: List[int] = []
            for choice in choices:
                search_txt = query
                if not search_txt:
                    continue
                first_letter_search_txt = search_txt[0]
                capital_search_txt = f"{first_letter_search_txt.upper()}{search_txt[1:]}"
                if search_txt in choice[1] or capital_search_txt in choice[1]:
                    index = choice[0]
                    if isinstance(index, int):
                        in_choices.append(index)
                    else:
                        current_filter = add_filter(
                            current_filter,
                            Q(**{f"{db_column}__icontains": index}),
                            optional=global_query is not None
                        )
            current_filter = add_filter(
                current_filter,
                Q(**{f"{db_column}__in": in_choices}),
                optional=global_query is not None
            )
        else:
            current_filter = add_filter(
                current_filter,
                Q(**{f"{db_column}__icontains": query}),
                optional=global_query is not None
            )

    if current_filter:
        return objects.filter(current_filter)
    return objects


def generate_datatables_records(
    request: HttpRequest,
    queryset: QuerySet,
    column_index_name_map: Dict[str, str],
    template_path: str
) -> HttpResponse:
    """
    Returns HttpResponse for use with datatables.

    :param queryset: Query, for which we're generating response
    :param column_index_name_map: datatables column names mapped to fields in
                                  query
    :param template_path: Template for our response
    """
    if not template_path:
        raise Exception("You must get template_path parameter.")

    searchable_columns = {
        request.GET.get(f'mDataProp_{col}', 'lp'):
        request.GET.get(f'sSearch_{col}', "")
        for col in range(int(request.GET.get('iColumns', 0)))
        if request.GET.get(f'bSearchable_{col}', "") == 'true'
    }

    text_to_search = request.GET.get('sSearch', '')
    if text_to_search:
        queryset = filter_queryset(
            queryset,
            searchable_columns,
            column_index_name_map,
            global_query=text_to_search
        )

    # Individual column search
    queryset = filter_queryset(
        queryset,
        searchable_columns,
        column_index_name_map
    )

    records_count = queryset.count()

    sorting_columns: List[Dict[str, Union[str, bool]]] = []
    id_used = False

    for i in range(int(request.GET.get("iSortingCols", 0))):
        col_id = int(request.GET.get(f"iSortCol_{i}", 0))

        if request.GET.get(f"bSortable_{col_id}", "false") != 'true':
            continue

        data_prop = request.GET.get(f"mDataProp_{col_id}", "id")
        col_name = column_index_name_map.get(data_prop, data_prop)

        sorting_columns.append({
            "ascending": request.GET.get(f'sSortDir_{i}', 'asc') == 'asc',
            "name": col_name
        })

        if col_name == "id":
            id_used = True

    if not id_used:
        sorting_columns.append({
            "name": "id",
            "ascending": True
        })

    queryset = order_queryset(queryset, sorting_columns)

    start_record = int(request.GET.get("iDisplayStart", 0))
    end_record = start_record + min(int(request.GET.get('iDisplayLength', 10)), 100)

    response = HttpResponse(
        render_to_string(template_path, {
            "sEcho": int(request.GET.get('sEcho', 0)),
            "iTotalRecords": records_count,
            "iTotalDisplayRecords": records_count,
            "querySet": queryset[start_record:end_record],
        }),
        content_type="application/javascript; charset=utf-8"
    )

    add_never_cache_headers(response)
    return response