import json
from django import http
from django.views import View


class AjaxView(View):
    """View that can be called only from Ajax."""

    def dispatch(self, request, *args, **kwargs):
        """Return super dispatch only if called from ajax."""
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return http.HttpResponseBadRequest()
        return super().dispatch(request, *args, **kwargs)


class JSONResponseMixin:
    """A mixin that can be used to render a JSON response."""

    response_class = http.HttpResponse

    def render_to_response(self, context, **response_kwargs):
        """Return a JSON response, transforming 'context' to make the payload."""
        response_kwargs.setdefault('content_type', 'application/json')
        return self.response_class(
            self.convert_context_to_json(context),
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        """Return converted context dictionary into a JSON object."""
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)
