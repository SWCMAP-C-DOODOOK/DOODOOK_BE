from django.contrib import admin

from apps.groups.models import Group, GroupMembership


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at", "updated_at")
    search_fields = ("name", "owner__username", "owner__email")
    list_filter = ("created_at",)


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "group",
        "user",
        "role",
        "status",
        "joined_at",
        "created_at",
    )
    list_filter = ("role", "status", "group")
    search_fields = ("group__name", "user__username", "user__email")
    autocomplete_fields = ("group", "user", "invited_by")
