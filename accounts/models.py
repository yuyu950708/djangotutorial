from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    email = models.EmailField(_("電子郵件"), unique=True)
    role = models.CharField(_("角色"), max_length=30, default="member")
    created_at = models.DateTimeField(_("建立時間"), auto_now_add=True)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        verbose_name = _("使用者")
        verbose_name_plural = _("使用者")

    def __str__(self) -> str:
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
        verbose_name=_("使用者"),
    )
    avatar = models.ImageField(_("大頭貼"), upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(_("自我介紹"), blank=True)
    dietary_preference = models.CharField(_("飲食偏好"), max_length=255, blank=True)

    class Meta:
        db_table = "profiles"
        verbose_name = _("個人資料")
        verbose_name_plural = _("個人資料")

    def __str__(self) -> str:
        return f"Profile({self.user.username})"


@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
