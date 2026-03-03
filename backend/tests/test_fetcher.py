"""core/data/fetcher.py 순수 함수 단위 테스트."""

import pandas as pd
import pytest

from core.data.fetcher import fetch_stock_listing


class TestFetchPriceDataRaw:
    def test_returns_dataframe_on_success(self, mocker):
        """네트워크 성공 시 DataFrame을 반환한다."""
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch("core.data.fetcher._retry", return_value=mock_df)

        from core.data.fetcher import fetch_price_data_raw

        df = fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")
        assert len(df) == 2
        assert "Close" in df.columns

    def test_returns_empty_dataframe_on_none(self, mocker):
        """네트워크가 None을 반환하면 빈 DataFrame을 반환한다."""
        mocker.patch("core.data.fetcher._retry", return_value=None)

        from core.data.fetcher import fetch_price_data_raw

        df = fetch_price_data_raw("005930", "2024-01-06", "2024-01-07")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_returns_empty_dataframe_on_empty_result(self, mocker):
        """네트워크가 빈 DataFrame을 반환하면 빈 DataFrame을 반환한다."""
        mocker.patch("core.data.fetcher._retry", return_value=pd.DataFrame())

        from core.data.fetcher import fetch_price_data_raw

        df = fetch_price_data_raw("005930", "2024-01-06", "2024-01-07")
        assert df.empty

    def test_propagates_network_error(self, mocker):
        """네트워크 오류는 그대로 전파한다."""
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("network error"))

        from core.data.fetcher import fetch_price_data_raw
        import pytest

        with pytest.raises(Exception, match="network error"):
            fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")


class TestFetchStockListingFallback:
    def test_uses_kospi_on_success(self, mocker):
        """KOSPI 성공 시 그대로 반환한다."""
        mock_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Stocks": [5_969_782_550],
        })
        mock_fdr = mocker.patch("core.data.fetcher.fdr.StockListing", return_value=mock_df)

        df = fetch_stock_listing("KOSPI")
        assert "Stocks" in df.columns
        assert len(df) == 1
        mock_fdr.assert_called_once_with("KOSPI")

    def test_falls_back_to_desc_on_kospi_failure(self, mocker):
        """KOSPI 실패 시 KOSPI-DESC로 fallback한다."""
        desc_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"],
            "Market": ["KOSPI"], "Sector": ["전기전자"],
        })
        mocker.patch(
            "core.data.fetcher.fdr.StockListing",
            side_effect=[Exception("KRX down"), desc_df],
        )

        df = fetch_stock_listing("KOSPI")
        assert "Code" in df.columns
        assert "Name" in df.columns
        assert "Stocks" not in df.columns
        assert len(df) == 1

    def test_raises_when_both_fail(self, mocker):
        """KOSPI, KOSPI-DESC 둘 다 실패 시 예외."""
        mocker.patch(
            "core.data.fetcher.fdr.StockListing",
            side_effect=Exception("KRX down"),
        )

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")

    def test_listing_uses_retry_1(self, mocker):
        """listing은 retry=1을 사용한다."""
        mocker.patch(
            "core.data.fetcher.fdr.StockListing",
            side_effect=Exception("fail"),
        )
        mock_sleep = mocker.patch("core.data.fetcher.time.sleep")

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")
        mock_sleep.assert_not_called()  # retry=1이면 sleep 없음


class TestFetchListingSharesFromNaver:
    def test_parses_listing_shares(self, mocker):
        """네이버 증권 HTML에서 상장주식수를 파싱한다."""
        html = '''
        <div id="tab_con1" class="tab_con1" style="display:block">
        <table>
        <tr><th scope="row">상장주식수</th><td><em>5,969,782,550</em></td></tr>
        </table>
        </div>
        '''
        mock_resp = mocker.Mock()
        mock_resp.text = html
        mock_resp.raise_for_status = mocker.Mock()
        mocker.patch("core.data.fetcher.requests.get", return_value=mock_resp)

        from core.data.fetcher import fetch_listing_shares_from_naver

        result = fetch_listing_shares_from_naver("005930")
        assert result == 5_969_782_550

    def test_returns_none_on_network_error(self, mocker):
        """네트워크 오류 시 None을 반환한다."""
        mocker.patch("core.data.fetcher.requests.get", side_effect=Exception("timeout"))

        from core.data.fetcher import fetch_listing_shares_from_naver

        result = fetch_listing_shares_from_naver("005930")
        assert result is None

    def test_returns_none_on_parse_failure(self, mocker):
        """파싱 실패 시 None을 반환한다."""
        mock_resp = mocker.Mock()
        mock_resp.text = "<html><body>no data</body></html>"
        mock_resp.raise_for_status = mocker.Mock()
        mocker.patch("core.data.fetcher.requests.get", return_value=mock_resp)

        from core.data.fetcher import fetch_listing_shares_from_naver

        result = fetch_listing_shares_from_naver("005930")
        assert result is None
