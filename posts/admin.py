from django.contrib import admin

from .models import Category, Collection, Comment, Follow, Like, Post, SearchLog, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "category", "like_count", "created_at")
    list_filter = ("category", "created_at", "updated_at")
    search_fields = ("title", "content", "author__username")
    filter_horizontal = ("tags",)


admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Follow)
admin.site.register(Collection)
admin.site.register(SearchLog)
