from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Like, Post, SearchLog, Tag
from .recommendations import get_today_meal_recommendations

User = get_user_model()


class TodayMealRecommendationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="foodie",
            email="foodie@example.com",
            password="test-pass",
        )
        self.author = User.objects.create_user(
            username="chef",
            email="chef@example.com",
            password="test-pass",
        )
        self.other_author = User.objects.create_user(
            username="snackboss",
            email="snackboss@example.com",
            password="test-pass",
        )
        self.noodle_category = Category.objects.create(name="麵食")
        self.dessert_category = Category.objects.create(name="甜點")
        self.spicy_tag = Tag.objects.create(name="微辣")
        self.sweet_tag = Tag.objects.create(name="甜食")

    def _post(self, *, title, author=None, category=None, tags=(), visibility=Post.VISIBILITY_PUBLIC, likes=0):
        post = Post.objects.create(
            author=author or self.author,
            category=category,
            title=title,
            content=f"<p>{title}</p>",
            visibility=visibility,
            like_count=likes,
        )
        if tags:
            post.tags.add(*tags)
        return post

    def test_recommendations_prioritize_user_interaction_preferences(self):
        seed = self._post(title="牛肉拉麵紀錄", category=self.noodle_category, tags=[self.spicy_tag])
        matching = self._post(title="今日豚骨拉麵", category=self.noodle_category, tags=[self.spicy_tag])
        unrelated_popular = self._post(
            title="超人氣甜甜圈",
            author=self.other_author,
            category=self.dessert_category,
            tags=[self.sweet_tag],
            likes=50,
        )
        Like.objects.create(user=self.user, post=seed)
        SearchLog.objects.create(user=self.user, keyword="拉麵")

        recommendations = get_today_meal_recommendations(self.user, limit=3)

        self.assertGreaterEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0].post.category, self.noodle_category)
        self.assertIn(recommendations[0].post, {seed, matching})
        self.assertTrue(recommendations[0].reason)
        self.assertIn(unrelated_popular, [rec.post for rec in recommendations])

    def test_recommendations_fall_back_to_public_posts_for_new_users(self):
        public_post = self._post(title="清爽雞肉飯", category=self.noodle_category)
        own_post = self._post(title="自己的晚餐", author=self.user, category=self.noodle_category)
        private_post = self._post(
            title="私密宵夜",
            category=self.dessert_category,
            visibility=Post.VISIBILITY_PRIVATE,
        )

        recommendations = get_today_meal_recommendations(self.user, limit=3)
        recommended_posts = [rec.post for rec in recommendations]

        self.assertIn(public_post, recommended_posts)
        self.assertNotIn(own_post, recommended_posts)
        self.assertNotIn(private_post, recommended_posts)

    def test_feed_shows_today_meal_recommendations_for_authenticated_homepage(self):
        recommended = self._post(title="今天適合吃雞肉飯", category=self.noodle_category)

        self.client.force_login(self.user)
        response = self.client.get(reverse("posts:feed"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "今天吃什麼？")
        self.assertContains(response, recommended.title)
