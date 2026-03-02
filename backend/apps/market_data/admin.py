"""시장 데이터 Admin."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import BatchMeta, StockDailyPrice, StockListing


@admin.register(BatchMeta)
class BatchMetaAdmin(ModelAdmin):
    list_display = ("job_name", "last_fetched_date", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(StockListing)
class StockListingAdmin(ModelAdmin):
    list_display = ("market", "code", "name", "market_cap")
    list_filter = ("market",)
    search_fields = ("code", "name")


@admin.register(StockDailyPrice)
class StockDailyPriceAdmin(ModelAdmin):
    list_display = ("code", "date", "close", "volume", "is_index")
    list_filter = ("is_index",)
    search_fields = ("code",)
