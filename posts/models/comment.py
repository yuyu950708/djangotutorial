from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Comment(models.Model):
    post = models.ForeignKey(
        "posts.Post",
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
