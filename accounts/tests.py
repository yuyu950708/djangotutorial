from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class SocialSignupTemplateTests(SimpleTestCase):
    def test_social_signup_template_extends_site_base(self):
        template = get_template("socialaccount/signup.html")
        source = template.template.source

        self.assertIn('extends "base.html"', source)
        self.assertIn("saas-card", source)
        self.assertIn("完成註冊", source)

    def test_social_connections_template_extends_site_base(self):
        template = get_template("socialaccount/connections.html")
        source = template.template.source

        self.assertIn('extends "base.html"', source)
        self.assertIn("saas-card", source)
        self.assertIn("連結 Google 帳號", source)

    def test_profile_edit_template_has_google_connect_link(self):
        template = get_template("accounts/profile_edit.html")
        source = template.template.source

        self.assertIn("連結 Google 帳號", source)
        self.assertIn("process='connect'", source)


class AuthTemplateTests(TestCase):
    def test_login_page_renders_google_login_link(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "使用 Google 登入")
        self.assertContains(response, "/oauth/google/login/")

    def test_register_page_renders_google_login_link(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "使用 Google 帳號繼續")
        self.assertContains(response, "/oauth/google/login/")


class LanguageSwitcherTests(TestCase):
    def test_nav_renders_language_switcher(self):
        response = self.client.get(reverse("posts:feed"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="zh-hant"')
        self.assertContains(response, 'value="en"')
        self.assertContains(response, reverse("set_language"))

    def test_set_language_switches_nav_to_english(self):
        session = self.client.session
        session["django_language"] = "en"
        session.save()

        response = self.client.get(reverse("posts:feed"))
        self.assertContains(response, "Home")
        self.assertContains(response, "Log in")
