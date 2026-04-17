from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        db_column="user_id",
        verbose_name=_("作者"),
    )
    category = models.ForeignKey(
        "posts.Category",
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
    tags = models.ManyToManyField("posts.Tag", related_name="posts", blank=True, verbose_name=_("標籤"))
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
