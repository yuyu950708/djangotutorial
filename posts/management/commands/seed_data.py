from django.core.management.base import BaseCommand

from posts.models import Category, Tag


DEFAULT_CATEGORIES = [
    "早餐",
    "早午餐",
    "午餐",
    "下午茶",
    "晚餐",
    "宵夜",
    "甜點",
    "零食",
    "飲料 / 手搖",
    "輕食 / 沙拉",
]

DEFAULT_TAGS = [
    "中式 / 台式",
    "日韓料理",
    "異國 / 西式",
    "小資平價",
    "約會聚餐",
    "快速外帶",
    "健康低卡",
    "素食友善",
    "無辣不歡",
    "踩雷勿近",
]


class Command(BaseCommand):
    help = "建立預設類別(Category)與標籤(Tag)資料"

    def handle(self, *args, **options):
        created_categories = 0
        created_tags = 0

        for name in DEFAULT_CATEGORIES:
            _, created = Category.objects.get_or_create(name=name)
            if created:
                created_categories += 1

        for name in DEFAULT_TAGS:
            _, created = Tag.objects.get_or_create(name=name)
            if created:
                created_tags += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"完成！新增 {created_categories} 筆類別、{created_tags} 筆標籤。"
            )
        )