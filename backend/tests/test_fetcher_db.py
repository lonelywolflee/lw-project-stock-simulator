"""시장 데이터 서비스 DB 연동 테스트."""

import datetime

import pandas as pd
import pytest

from apps.market_data.models import BatchMeta, PriceFetchCoverage, StockDailyPrice, StockListing
from apps.market_data.services import (
    _find_uncovered_ranges,
    _save_coverage,
    fetch_all_prices,
    fetch_kospi_index,
    fetch_price_data,
    fetch_stock_listing,
)


@pytest.mark.django_db
class TestFetchStockListingDB:
    def test_returns_db_data_when_batch_is_today(self):
        """오늘 배치 완료 시 DB 데이터를 반환한다."""
        StockListing.objects.create(market="KOSPI", code="005930", name="삼성전자", market_cap=500_000_000_000)
        StockListing.objects.create(market="KOSPI", code="000660", name="SK하이닉스", market_cap=100_000_000_000)
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
        mocker.patch("core.data.fetcher._fetch_listing_with_fallback", return_value=mock_df)

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert StockListing.objects.count() == 1
        assert BatchMeta.objects.filter(job_name="kospi_listing").exists()

    def test_uses_db_fallback_on_network_error(self, mocker):
        """네트워크 실패 시 기존 DB 데이터를 반환한다."""
        StockListing.objects.create(market="KOSPI", code="005930", name="삼성전자", market_cap=500_000_000_000)
        mocker.patch("core.data.fetcher._fetch_listing_with_fallback", side_effect=Exception("network error"))

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert df.iloc[0]["Code"] == "005930"

    def test_raises_when_no_db_and_network_fails(self, mocker):
        """DB도 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch("core.data.fetcher._fetch_listing_with_fallback", side_effect=Exception("network error"))

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")


@pytest.mark.django_db
class TestFetchPriceDataDB:
    def test_returns_db_data_when_fully_covered(self):
        """전체 커버 시 네트워크 요청 없이 DB에서 반환한다."""
        for day, close in [(2, 103), (3, 106)]:
            StockDailyPrice.objects.create(
                code="005930", date=datetime.date(2024, 1, day),
                open=100, high=105, low=99, close=close, volume=1000,
            )
            PriceFetchCoverage.objects.create(
                code="005930", date=datetime.date(2024, 1, day), has_data=True,
            )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert df.iloc[0]["Close"] == 103

    def test_fetches_only_uncovered_range(self, mocker):
        """캐시된 부분은 건너뛰고 미캐시 구간만 네트워크 fetch한다."""
        # 01-02 캐시됨
        StockDailyPrice.objects.create(
            code="005930", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        PriceFetchCoverage.objects.create(
            code="005930", date=datetime.date(2024, 1, 2), has_data=True,
        )

        # 01-03~04 미캐시 → 네트워크 fetch
        dates = pd.to_datetime(["2024-01-03", "2024-01-04"])
        mock_df = pd.DataFrame({
            "Open": [103, 105], "High": [107, 109],
            "Low": [102, 104], "Close": [106, 108],
            "Volume": [1200, 1100],
        }, index=dates)
        mock_raw = mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-04")

        assert len(df) == 3
        assert df.iloc[0]["Close"] == 103  # DB
        assert df.iloc[1]["Close"] == 106  # 네트워크
        mock_raw.assert_called_once()

    def test_handles_non_trading_days(self, mocker):
        """비거래일이 포함된 범위를 정상 처리한다."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-04")

        assert len(df) == 2  # 비거래일 01-04 제외
        assert PriceFetchCoverage.objects.filter(code="005930").count() == 3
        assert PriceFetchCoverage.objects.filter(code="005930", has_data=False).count() == 1

    def test_second_call_uses_cache(self, mocker):
        """두 번째 동일 호출은 네트워크 요청 없이 캐시에서 반환한다."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mock_raw = mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        fetch_price_data("005930", "2024-01-02", "2024-01-03")
        assert mock_raw.call_count == 1

        df2 = fetch_price_data("005930", "2024-01-02", "2024-01-03")
        assert mock_raw.call_count == 1  # 추가 호출 없음
        assert len(df2) == 2

    def test_fetches_from_network_and_saves(self, mocker):
        """DB에 없으면 네트워크 fetch 후 DB에 저장한다."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert StockDailyPrice.objects.filter(code="005930").count() == 2
        assert PriceFetchCoverage.objects.filter(code="005930").count() == 2

    def test_raises_on_network_failure(self, mocker):
        """DB에 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            side_effect=Exception("fail"),
        )

        with pytest.raises(Exception):
            fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert PriceFetchCoverage.objects.count() == 0


@pytest.mark.django_db
class TestFetchKospiIndexDB:
    def test_returns_db_data_when_fully_covered(self):
        """전체 커버 시 DB에서 반환한다."""
        StockDailyPrice.objects.create(
            code="KS11", date=datetime.date(2024, 1, 2),
            open=2500, high=2520, low=2490, close=2510, volume=0, is_index=True,
        )
        PriceFetchCoverage.objects.create(
            code="KS11", date=datetime.date(2024, 1, 2), has_data=True,
        )

        df = fetch_kospi_index("2024-01-02", "2024-01-02")

        assert len(df) == 1
        assert df.iloc[0]["Close"] == 2510

    def test_second_call_uses_cache(self, mocker):
        """두 번째 동일 호출은 캐시에서 반환한다."""
        dates = pd.to_datetime(["2024-01-02"])
        mock_df = pd.DataFrame({
            "Open": [2500], "High": [2520],
            "Low": [2490], "Close": [2510],
            "Volume": [0],
        }, index=dates)
        mock_raw = mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        fetch_kospi_index("2024-01-02", "2024-01-02")
        assert mock_raw.call_count == 1

        fetch_kospi_index("2024-01-02", "2024-01-02")
        assert mock_raw.call_count == 1  # 추가 호출 없음


@pytest.mark.django_db
class TestFetchAllPricesDB:
    def test_skips_failed_stock_and_continues(self, mocker):
        """한 종목 실패 시 건너뛰고 나머지 진행."""
        StockDailyPrice.objects.create(
            code="A", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        PriceFetchCoverage.objects.create(
            code="A", date=datetime.date(2024, 1, 2), has_data=True,
        )
        # B는 DB에도 없고 네트워크도 실패
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            side_effect=Exception("fail"),
        )

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
        mocker.patch("core.data.fetcher._fetch_listing_with_fallback", side_effect=[listing_df])
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=price_df,
        )

        listing = fetch_stock_listing("KOSPI")
        assert len(listing) == 1

        prices = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices) == 3

        # 두 번째 호출은 DB에서 가져옴
        prices2 = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices2) == 3


@pytest.mark.django_db
class TestFindUncoveredRanges:
    def test_returns_full_range_when_no_coverage(self):
        """커버리지가 없으면 전체 범위를 반환한다."""
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-04")
        assert result == [("2024-01-02", "2024-01-04")]

    def test_returns_empty_when_fully_covered(self):
        """전체가 커버되면 빈 리스트를 반환한다."""
        for day in range(2, 5):
            PriceFetchCoverage.objects.create(
                code="005930", date=datetime.date(2024, 1, day), has_data=True,
            )
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-04")
        assert result == []

    def test_returns_tail_range_when_partially_covered(self):
        """앞부분만 커버되면 뒷부분만 반환한다."""
        for day in range(2, 5):
            PriceFetchCoverage.objects.create(
                code="005930", date=datetime.date(2024, 1, day), has_data=True,
            )
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-06")
        assert result == [("2024-01-05", "2024-01-06")]

    def test_returns_multiple_uncovered_ranges(self):
        """비연속적인 다중 미커버 구간을 반환한다."""
        PriceFetchCoverage.objects.create(code="005930", date=datetime.date(2024, 1, 2), has_data=True)
        PriceFetchCoverage.objects.create(code="005930", date=datetime.date(2024, 1, 3), has_data=True)
        PriceFetchCoverage.objects.create(code="005930", date=datetime.date(2024, 1, 5), has_data=True)

        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-07")
        assert result == [("2024-01-04", "2024-01-04"), ("2024-01-06", "2024-01-07")]

    def test_ignores_other_codes(self):
        """다른 종목의 커버리지는 무시한다."""
        PriceFetchCoverage.objects.create(code="000660", date=datetime.date(2024, 1, 2), has_data=True)
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-02")
        assert result == [("2024-01-02", "2024-01-02")]


@pytest.mark.django_db
class TestSaveCoverage:
    def test_saves_coverage_for_all_dates(self):
        """fetch 범위의 모든 날짜에 커버리지를 저장한다."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-04"])
        df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)

        _save_coverage("005930", "2024-01-02", "2024-01-04", df)

        coverages = list(
            PriceFetchCoverage.objects.filter(code="005930")
            .order_by("date").values_list("date", "has_data")
        )
        assert len(coverages) == 3
        assert coverages[0] == (datetime.date(2024, 1, 2), True)
        assert coverages[1] == (datetime.date(2024, 1, 3), False)  # 비거래일
        assert coverages[2] == (datetime.date(2024, 1, 4), True)

    def test_saves_all_no_data_for_empty_df(self):
        """빈 DataFrame이면 모든 날짜를 비거래일로 기록한다."""
        _save_coverage("005930", "2024-01-06", "2024-01-07", pd.DataFrame())

        coverages = list(
            PriceFetchCoverage.objects.filter(code="005930")
            .order_by("date").values_list("has_data", flat=True)
        )
        assert coverages == [False, False]

    def test_ignores_conflicts_on_duplicate(self):
        """중복 저장 시 충돌을 무시한다."""
        PriceFetchCoverage.objects.create(
            code="005930", date=datetime.date(2024, 1, 2), has_data=True,
        )
        _save_coverage("005930", "2024-01-02", "2024-01-02", pd.DataFrame())

        assert PriceFetchCoverage.objects.filter(code="005930").count() == 1
