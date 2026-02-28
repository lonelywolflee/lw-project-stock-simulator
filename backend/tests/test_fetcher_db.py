"""시장 데이터 서비스 DB 연동 테스트."""

import datetime

import pandas as pd
import pytest

from apps.market_data.models import BatchMeta, StockDailyPrice, StockListing
from apps.market_data.services import (
    fetch_all_prices,
    fetch_kospi_index,
    fetch_price_data,
    fetch_stock_listing,
)


@pytest.mark.django_db
class TestFetchStockListingDB:
    def test_returns_db_data_when_batch_is_today(self):
        """오늘 배치 완료 시 DB 데이터를 반환한다."""
        StockListing.objects.create(code="005930", name="삼성전자", market_cap=500_000_000_000)
        StockListing.objects.create(code="000660", name="SK하이닉스", market_cap=100_000_000_000)
        BatchMeta.objects.create(job_name="kospi_listing", last_fetched_date=datetime.date.today())

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 2
        assert "Code" in df.columns
        assert "Name" in df.columns
        assert "Marcap" in df.columns

    def test_fetches_from_network_when_no_batch(self, mocker):
        """배치 기록이 없으면 네트워크에서 fetch하고 DB에 저장한다."""
        mock_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Marcap": [500_000_000_000],
        })
        mocker.patch("core.data.fetcher._retry", return_value=mock_df)

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert StockListing.objects.count() == 1
        assert BatchMeta.objects.filter(job_name="kospi_listing").exists()

    def test_uses_db_fallback_on_network_error(self, mocker):
        """네트워크 실패 시 기존 DB 데이터를 반환한다."""
        StockListing.objects.create(code="005930", name="삼성전자", market_cap=500_000_000_000)
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("network error"))

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert df.iloc[0]["Code"] == "005930"

    def test_raises_when_no_db_and_network_fails(self, mocker):
        """DB도 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("network error"))

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")


@pytest.mark.django_db
class TestFetchPriceDataDB:
    def test_returns_db_data_when_exists(self):
        """DB에 데이터가 있으면 DB에서 반환한다."""
        StockDailyPrice.objects.create(
            code="005930", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        StockDailyPrice.objects.create(
            code="005930", date=datetime.date(2024, 1, 3),
            open=103, high=107, low=102, close=106, volume=1200,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert "Close" in df.columns
        assert df.iloc[0]["Close"] == 103

    def test_fetches_from_network_and_saves(self, mocker):
        """DB에 없으면 네트워크 fetch 후 DB에 저장한다."""
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch("core.data.fetcher._retry", return_value=mock_df)

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert StockDailyPrice.objects.filter(code="005930").count() == 2

    def test_raises_on_network_failure(self, mocker):
        """DB에 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("fail"))

        with pytest.raises(Exception):
            fetch_price_data("005930", "2024-01-02", "2024-01-03")


@pytest.mark.django_db
class TestFetchKospiIndexDB:
    def test_returns_db_data_when_exists(self):
        """DB에 KS11 데이터가 있으면 반환한다."""
        StockDailyPrice.objects.create(
            code="KS11", date=datetime.date(2024, 1, 2),
            open=2500, high=2520, low=2490, close=2510, volume=0, is_index=True,
        )

        df = fetch_kospi_index("2024-01-02", "2024-01-02")

        assert len(df) == 1
        assert df.iloc[0]["Close"] == 2510


@pytest.mark.django_db
class TestFetchAllPricesDB:
    def test_skips_failed_stock_and_continues(self, mocker):
        """한 종목 실패 시 건너뛰고 나머지 진행."""
        StockDailyPrice.objects.create(
            code="A", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        # B는 DB에도 없고 네트워크도 실패
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("fail"))

        result = fetch_all_prices(["A", "B"], "2024-01-02", "2024-01-02")

        assert "A" in result
        assert "B" not in result


@pytest.mark.django_db
class TestIntegrationFlow:
    def test_listing_then_price_flow(self, mocker):
        """종목 목록 → 가격 조회 전체 흐름."""
        listing_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Marcap": [500_000_000_000],
        })
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        price_df = pd.DataFrame({
            "Open": [70000, 71000, 72000],
            "High": [71000, 72000, 73000],
            "Low": [69000, 70000, 71000],
            "Close": [70500, 71500, 72500],
            "Volume": [10000, 12000, 11000],
        }, index=dates)
        mocker.patch("core.data.fetcher._retry", side_effect=[listing_df, price_df])

        listing = fetch_stock_listing("KOSPI")
        assert len(listing) == 1

        prices = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices) == 3

        # 두 번째 호출은 DB에서 가져옴 (mock이 소진되어도 OK)
        prices2 = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices2) == 3
