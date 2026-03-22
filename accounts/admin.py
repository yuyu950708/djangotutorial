from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Profile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_staff", "created_at")
    search_fields = ("username", "email", "role")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Eat What", {"fields": ("role", "created_at")}),
    )
    readonly_fields = ("created_at",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "dietary_preference")
    search_fields = ("user__username", "user__email", "dietary_preference")
