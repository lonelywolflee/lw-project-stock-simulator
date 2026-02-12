"""URL 설정."""

from django.urls import path
from ninja import NinjaAPI

from apps.backtests.api import router as backtests_router
from apps.market_data.api import router as market_data_router

api = NinjaAPI(
    title="Stock Simulator API",
    version="1.0.0",
    description="KOSPI + NASDAQ 이중 시장 백테스트 시뮬레이터 API",
)

api.add_router("/backtests", backtests_router)
api.add_router("/market-data", market_data_router)

urlpatterns = [
    path("api/", api.urls),
]
