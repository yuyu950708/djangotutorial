from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.db import models
from django.db.models import F
from django.db.models.functions import Greatest
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(_("名稱"), max_length=100)

    class Meta:
        db_table = "categories"
        ordering = ["name"]
        verbose_name = _("分類")
        verbose_name_plural = _("分類")

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    name = models.CharField(_("名稱"), max_length=100, unique=True)

    class Meta:
        db_table = "tags"
        ordering = ["name"]
        verbose_name = _("標籤")
        verbose_name_plural = _("標籤")

    def __str__(self) -> str:
        return self.name


class SearchLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_logs",
        verbose_name=_("使用者"),
    )
    keyword = models.CharField(_("關鍵字"), max_length=255)
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)

    class Meta:
        db_table = "search_logs"
        ordering = ["-created_at"]
        verbose_name = _("搜尋紀錄")
        verbose_name_plural = _("搜尋紀錄")

    def __str__(self) -> str:
        return f"SearchLog({self.user.username}: {self.keyword})"


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        db_column="user_id",
        verbose_name=_("作者"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="posts",
        blank=True,
        null=True,
        verbose_name=_("分類"),
    )
    title = models.CharField(_("標題"), max_length=255, blank=True)
    content = RichTextUploadingField(_("內容"))
    image = models.ImageField(
        _("圖片"),
        upload_to="posts/",
        db_column="image_url",
        blank=True,
        null=True,
    )
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True, verbose_name=_("標籤"))
    like_count = models.PositiveIntegerField(_("讚數"), default=0)
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)
    updated_at = models.DateTimeField(_("更新時間"), auto_now=True)

    class Meta:
        db_table = "posts"
        ordering = ["-created_at", "-id"]
        verbose_name = _("貼文")
        verbose_name_plural = _("貼文")

    def __str__(self) -> str:
        headline = self.title or self.content[:20]
        return f"Post({self.author.username}: {headline})"


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name=_("使用者"),
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name=_("貼文"),
    )
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)

    class Meta:
        db_table = "likes"
        verbose_name = _("按讚")
        verbose_name_plural = _("按讚")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_like_per_user_post",
            )
        ]

    def __str__(self) -> str:
        return f"Like({self.user.username} -> {self.post_id})"


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("貼文"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        db_column="user_id",
        verbose_name=_("作者"),
    )
    content = models.TextField(_("內容"))
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]
        verbose_name = _("留言")
        verbose_name_plural = _("留言")

    def __str__(self) -> str:
        return f"Comment({self.author.username} -> {self.post_id})"


class PostComment(models.Model):
    content = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_comments",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="post_comments",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    root = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="descendants",
    )
    is_locked = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    like_count = models.PositiveIntegerField(_("讚數"), default=0)

    class Meta:
        db_table = "post_comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "created_at"], name="post_comment_post_created"),
            models.Index(fields=["root", "created_at"], name="post_comment_root_created"),
            models.Index(fields=["parent", "created_at"], name="post_comment_parent_created"),
        ]

    def __str__(self) -> str:
        return f"PostComment({self.author_id} -> {self.post_id})"


class CommentLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_likes",
        verbose_name=_("使用者"),
    )
    comment = models.ForeignKey(
        PostComment,
        on_delete=models.CASCADE,
        related_name="comment_likes",
        verbose_name=_("留言"),
    )
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)

    class Meta:
        db_table = "post_comment_likes"
        verbose_name = _("留言讚")
        verbose_name_plural = _("留言讚")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "comment"],
                name="unique_comment_like_per_user_comment",
            )
        ]

    def __str__(self) -> str:
        return f"CommentLike({self.user_id} -> comment {self.comment_id})"


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following_relationships",
        verbose_name=_("追蹤者"),
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follower_relationships",
        verbose_name=_("被追蹤者"),
    )
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)

    class Meta:
        db_table = "follows"
        verbose_name = _("追蹤關係")
        verbose_name_plural = _("追蹤關係")
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_follow_pair",
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=F("following")),
                name="prevent_self_follow",
            ),
        ]

    def __str__(self) -> str:
        return f"Follow({self.follower.username} -> {self.following.username})"


class Collection(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collections",
        verbose_name=_("使用者"),
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="collections",
        verbose_name=_("貼文"),
    )
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)

    class Meta:
        db_table = "collections"
        verbose_name = _("收藏")
        verbose_name_plural = _("收藏")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_collection_per_user_post",
            )
        ]

    def __str__(self) -> str:
        return f"Collection({self.user.username} -> {self.post_id})"


@receiver(post_save, sender=Like)
def increment_like_count(sender, instance, created, **kwargs):
    if created:
        Post.objects.filter(pk=instance.post_id).update(like_count=F("like_count") + 1)


@receiver(post_delete, sender=Like)
def decrement_like_count(sender, instance, **kwargs):
    Post.objects.filter(pk=instance.post_id).update(like_count=Greatest(F("like_count") - 1, 0))


@receiver(post_save, sender=CommentLike)
def increment_comment_like_count(sender, instance, created, **kwargs):
    if created:
        PostComment.objects.filter(pk=instance.comment_id).update(like_count=F("like_count") + 1)


@receiver(post_delete, sender=CommentLike)
def decrement_comment_like_count(sender, instance, **kwargs):
    PostComment.objects.filter(pk=instance.comment_id).update(like_count=Greatest(F("like_count") - 1, 0))
