"""시장 데이터 Django 모델."""

from django.db import models


class BatchMeta(models.Model):
    """배치 작업 메타 정보 — 마지막 fetch 일자를 추적한다."""

    job_name = models.CharField(max_length=100, unique=True)
    last_fetched_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_data_batch_meta"

    def __str__(self):
        return f"{self.job_name} ({self.last_fetched_date})"


class StockListing(models.Model):
    """KOSPI 상장 종목 정보."""

    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    market_cap = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "market_data_stock_listing"

    def __str__(self):
        return f"{self.code} {self.name}"


class StockDailyPrice(models.Model):
    """종목 및 지수의 일별 OHLCV 데이터."""

    code = models.CharField(max_length=20, db_index=True)
    date = models.DateField(db_index=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.BigIntegerField()
    is_index = models.BooleanField(default=False)

    class Meta:
        db_table = "market_data_stock_daily_price"
        unique_together = [("code", "date")]
        indexes = [
            models.Index(fields=["code", "date"]),
        ]

    def __str__(self):
        return f"{self.code} {self.date} C={self.close}"
