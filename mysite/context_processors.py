from django.db.models import Count

from posts.models import Category


def wheel_categories(request):
    """分類轉盤：僅含至少一篇貼文的分類，依貼文數與名稱排序，最多 16 格。"""
    items = list(
        Category.objects.annotate(_post_count=Count("posts", distinct=True))
        .filter(_post_count__gt=0)
        .order_by("-_post_count", "name")[:16]
        .values("id", "name")
    )
    return {"wheel_category_items": items}
