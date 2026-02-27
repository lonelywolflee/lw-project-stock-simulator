"""URL 설정."""

from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView
from ninja import NinjaAPI

from apps.accounts.api import router as auth_router
from apps.backtests.api import router as backtests_router
from apps.market_data.api import router as market_data_router

api = NinjaAPI(
    title="Stock Simulator API",
    version="1.0.0",
    description="KOSPI 백테스트 시뮬레이터 API",
)

api.add_router("/auth", auth_router)
api.add_router("/backtests", backtests_router)
api.add_router("/market-data", market_data_router)

urlpatterns = [
    path("admin/login/", RedirectView.as_view(url="/login/", query_string=True)),
    path("admin/logout/", RedirectView.as_view(url="/login/")),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
