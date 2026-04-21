import csv
from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponse
from import_export import resources
from import_export.admin import ExportMixin

from .models import (
    AiChatLog,
    Category,
    Collection,
    CommentLike,
    Follow,
    Like,
    Post,
    PostComment,
    PostHealthInsight,
    SearchLog,
    Tag,
)


class PostResource(resources.ModelResource):
    class Meta:
        model = Post
        fields = ("id", "title", "author__username", "category__name", "like_count", "created_at", "updated_at")


class CommentInline(admin.TabularInline):
    model = PostComment
    fields = ("author", "content", "created_at")
    readonly_fields = ("created_at",)
    extra = 0
    autocomplete_fields = ("author",)


@admin.action(description="重算選取貼文的 like_count")
def recalc_like_count(modeladmin, request, queryset):
    post_ids = list(queryset.values_list("id", flat=True))
    counts = dict(
        Like.objects.filter(post_id__in=post_ids)
        .values_list("post_id")
        .annotate(c=Count("id"))
        .values_list("post_id", "c")
    )
    for post_id in post_ids:
        Post.objects.filter(id=post_id).update(like_count=counts.get(post_id, 0))


@admin.action(description="匯出選取貼文為 CSV")
def export_posts_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="posts.csv"'
    writer = csv.writer(response)
    writer.writerow(["id", "title", "author", "category", "like_count", "created_at"])
    for post in queryset.select_related("author", "category").order_by("-created_at"):
        writer.writerow(
            [
                post.id,
                post.title,
                post.author.username,
                post.category.name if post.category else "",
                post.like_count,
                post.created_at.isoformat(),
            ]
        )
    return response


@admin.register(Post)
class PostAdmin(ExportMixin, admin.ModelAdmin):
    resource_classes = [PostResource]
    inlines = [CommentInline]

    # MySQL 未安裝 timezone tables 時，date_hierarchy 會觸發時區換算錯誤。
    # 先停用階層日期導覽，避免 /admin/posts/post/ 500。
    date_hierarchy = None
    list_display = ("id", "title", "author", "category", "like_count", "created_at")
    list_filter = ("category", "tags", "author", "created_at", "updated_at")
    search_fields = ("title", "content", "author__username", "author__email")
    ordering = ("-created_at",)
    list_per_page = 25
    list_select_related = ("author", "category")

    autocomplete_fields = ("author", "category", "tags")
    filter_horizontal = ("tags",)

    actions = (recalc_like_count, export_posts_csv)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "comment", "created_at")
    list_select_related = ("user", "comment", "comment__post")
    ordering = ("-created_at",)


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "like_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "author__username", "author__email", "post__title")
    autocomplete_fields = ("post", "author")
    ordering = ("-created_at",)
    list_select_related = ("post", "author")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "user__email", "post__title")
    autocomplete_fields = ("post", "user")
    ordering = ("-created_at",)
    list_select_related = ("post", "user")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "following", "created_at")
    list_filter = ("created_at",)
    search_fields = ("follower__username", "following__username")
    autocomplete_fields = ("follower", "following")
    ordering = ("-created_at",)
    list_select_related = ("follower", "following")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "user__email", "post__title")
    autocomplete_fields = ("user", "post")
    ordering = ("-created_at",)
    list_select_related = ("user", "post")


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "keyword", "created_at")
    list_filter = ("created_at",)
    search_fields = ("keyword", "user__username", "user__email")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)
    list_select_related = ("user",)


@admin.register(AiChatLog)
class AiChatLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "model_name", "message", "has_image", "created_at")
    list_filter = ("created_at",)
    search_fields = ("message", "assistant_reply", "model_name", "user__username", "user__email")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)
    list_select_related = ("user",)

    @admin.display(description="有圖片")
    def has_image(self, obj):
        return bool(obj.image)


@admin.register(PostHealthInsight)
class PostHealthInsightAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "health_rank", "calories", "status", "model_name", "created_at")
    list_filter = ("health_rank", "status", "created_at")
    search_fields = ("post__title", "post__author__username", "reason", "model_name")
    autocomplete_fields = ("post",)
    ordering = ("-created_at",)
    list_select_related = ("post",)
