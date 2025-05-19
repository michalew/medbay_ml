from django.template.defaulttags import register
from django.template.loader import get_template


@register.inclusion_tag('simple_history/inline_history_dummy.html')
def inline_history(obj):
    template = "simple_history/inline_history.html"
    custom_template = f"simple_history/inline_history__{obj._meta.model_name}.html"

    print(custom_template)

    try:
        get_template(custom_template)
        template = custom_template
    except:
        pass

    return {'obj': obj, 'template': template}
