"""시장 데이터 Admin."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import BatchMeta, PriceFetchCoverage, StockDailyPrice, StockListing


@admin.register(BatchMeta)
class BatchMetaAdmin(ModelAdmin):
    list_display = ("job_name", "last_fetched_date", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(StockListing)
class StockListingAdmin(ModelAdmin):
    list_display = ("market", "code", "name", "listing_shares", "listing_shares_updated_at")
    list_filter = ("market",)
    search_fields = ("code", "name")


@admin.register(StockDailyPrice)
class StockDailyPriceAdmin(ModelAdmin):
    list_display = ("market", "code", "date", "close", "volume", "is_index")
    list_filter = ("market", "is_index")
    search_fields = ("code",)


@admin.register(PriceFetchCoverage)
class PriceFetchCoverageAdmin(ModelAdmin):
    list_display = ("market", "code", "date", "has_data")
    list_filter = ("market", "has_data")
    search_fields = ("code",)
