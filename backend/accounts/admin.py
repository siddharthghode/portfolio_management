from django.contrib import admin
from .models import Portfolio, Project, UserSession, SecurityEvent


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["full_name", "user", "headline", "created_at"]
    search_fields = ["full_name", "user__username"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "portfolio", "tech_stack", "created_at"]
    search_fields = ["title", "portfolio__user__username"]


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "device_name", "device_type", "browser", "ip_address", "created_at", "status"]
    list_filter = ["device_type", "revoked_at"]
    search_fields = ["user__username", "device_name", "ip_address"]
    readonly_fields = ["id", "session_key_hash", "created_at", "last_seen_at", "last_refresh_at"]

    def status(self, obj):
        return obj.status
    status.short_description = "Status"


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "ip_address", "detail", "created_at"]
    list_filter = ["event_type"]
    search_fields = ["user__username", "ip_address", "detail"]
    readonly_fields = ["id", "created_at"]
