"""core/data/fetcher.py 순수 함수 단위 테스트."""

import pandas as pd


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
