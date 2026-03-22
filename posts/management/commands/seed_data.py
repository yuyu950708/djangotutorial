from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from posts.models import Category, Post, Tag


class Command(BaseCommand):
    help = "Seed categories, tags, and sample posts for local development."

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        admin_user = user_model.objects.filter(is_superuser=True).order_by("id").first()
        if admin_user is None:
            raise CommandError("No superuser found. Please create a superuser before seeding data.")

        categories = {
            name: Category.objects.get_or_create(name=name)[0]
            for name in ("中式", "日式", "美式")
        }
        tags = {
            name: Tag.objects.get_or_create(name=name)[0]
            for name in ("辣", "健康", "便宜")
        }

        seed_posts = [
            {
                "title": "深夜也想吃的川味牛肉麵",
                "category": categories["中式"],
                "content": (
                    "<p>這是一篇測試貼文，想吃點香辣又有飽足感的中式料理。</p>"
                    "<p>圖片 URL：https://placehold.co/1200x800/png?text=Chinese+Food</p>"
                ),
                "tag_names": ["辣", "便宜"],
            },
            {
                "title": "清爽系鮭魚定食午餐",
                "category": categories["日式"],
                "content": (
                    "<p>這是一篇測試貼文，適合想吃得清爽一點的日式選擇。</p>"
                    "<p>圖片 URL：https://placehold.co/1200x800/png?text=Japanese+Set</p>"
                ),
                "tag_names": ["健康", "便宜"],
            },
        ]

        created_count = 0
        updated_count = 0

        for seed_post in seed_posts:
            post, created = Post.objects.get_or_create(
                title=seed_post["title"],
                author=admin_user,
                defaults={
                    "category": seed_post["category"],
                    "content": seed_post["content"],
                },
            )
            if created:
                created_count += 1
            else:
                post.category = seed_post["category"]
                post.content = seed_post["content"]
                post.save(update_fields=["category", "content", "updated_at"])
                updated_count += 1

            post.tags.set([tags[name] for name in seed_post["tag_names"]])

        self.stdout.write(self.style.SUCCESS(f"Seed completed. Created {created_count} post(s), updated {updated_count} post(s)."))
        self.stdout.write(f"Seed author: {admin_user.username}")
