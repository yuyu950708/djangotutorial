from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Profile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_staff", "created_at")
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "date_joined")
    search_fields = ("username", "email", "role")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("等等吃啥", {"fields": ("role", "created_at")}),
    )
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "dietary_preference")
    search_fields = ("user__username", "user__email", "dietary_preference")
    autocomplete_fields = ("user",)
