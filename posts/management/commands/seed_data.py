import random
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from posts.models import Category, Post, Tag

SEED_MARKER = ""

# 對應 media/posts/ 裡的 4 張照片
LOCAL_POST_IMAGES = [
    "posts/1.jpg",
    "posts/2.jpg",
    "posts/3.jpg",
    "posts/4.jpg",
]

# 簡潔有力的文案
SEED_POSTS = [
    {"title": "超好吃拉麵", "body": "這家真的好吃，推！🍜"},
    {"title": "吃土首選", "body": "份量超足，好吃！"},
    {"title": "經典甜點", "body": "這家甜點讚，必吃。"},
    {"title": "推薦拉麵", "body": "湯頭很讚，好吃！"},
]

class Command(BaseCommand):
    help = "建立 4 篇簡單的測試貼文。"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            raise CommandError("找不到超級管理員，請先跑 createsuperuser！")

        # 確保分類與標籤存在
        cats = [Category.objects.get_or_create(name=n)[0] for n in ("中式", "日式", "美式")]
        tgs = [Tag.objects.get_or_create(name=n)[0] for n in ("辣", "健康", "便宜")]

        # 清除舊的測試資料
        Post.objects.filter(content__contains=SEED_MARKER).delete()

        rng = random.SystemRandom()

        for i, seed in enumerate(SEED_POSTS):
            image_filename = LOCAL_POST_IMAGES[i]
            image_url = f"{settings.MEDIA_URL}{image_filename}"
            
            content = (
                f"{SEED_MARKER}"
                f"<p>{seed['body']}</p>"
                f"<img src='{image_url}' style='max-width:100%; height:auto; border-radius:8px;'>"
            )

            post = Post.objects.create(
                author=admin_user,
                category=rng.choice(cats),
                title=seed["title"],
                content=content,
            )
            post.tags.set(rng.sample(tgs, k=rng.randint(1, 2)))

        self.stdout.write(self.style.SUCCESS(f"成功建立 {len(SEED_POSTS)} 篇測試文！"))