from django.contrib import admin
from .models import Profile, DataRequest


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email_verified", "created_at")
    search_fields = ("user__email", "user__username")


@admin.register(DataRequest)
class DataRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "requested_at", "status", "answered_at", "export_hash")
    list_filter = ("status", "requested_at")
    search_fields = ("user__email", "user__username")
