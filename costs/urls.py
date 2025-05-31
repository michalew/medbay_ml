from django.urls import path
from django.contrib.auth.decorators import login_required
from costs.views import CostsView, CostsRangeView

urlpatterns = [
    path('', login_required(CostsView.as_view()), name='costs'),
    path('zakres', login_required(CostsRangeView.as_view()), name='costs_range'),
]