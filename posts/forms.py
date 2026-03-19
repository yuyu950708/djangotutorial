import bleach
from bleach.css_sanitizer import ALLOWED_CSS_PROPERTIES, CSSSanitizer
from django import forms
from django.conf import settings
from django.utils.html import strip_tags

from .models import Post

# 使用 Bleach 內建允許的 CSS 屬性（含 font / font-size / font-family / color 等），
# 避免 CKEditor 用 font 縮寫時整段 style 被清掉。
_EXTRA_CSS = frozenset(
    {
        "max-width",
        "max-height",
        "min-width",
        "min-height",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "border",
        "border-collapse",
        "border-spacing",
        "border-color",
        "border-width",
        "border-style",
        "border-top",
        "border-right",
        "border-bottom",
        "border-left",
        "box-sizing",
        "background",
        "background-image",
        "list-style",
        "list-style-type",
    }
)

_CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=ALLOWED_CSS_PROPERTIES | _EXTRA_CSS,
)


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("content", "image")
        widgets = {
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "block w-full cursor-pointer rounded-lg border border-slate-300 text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-slate-700 hover:file:bg-slate-200",
                }
            ),
        }

    def clean_content(self):
        value = self.cleaned_data.get("content") or ""
        text_only = strip_tags(value).replace("\xa0", " ").strip()
        if not text_only:
            raise forms.ValidationError("請輸入貼文內容。")
        return bleach.clean(
            value,
            tags=settings.BLEACH_ALLOWED_TAGS,
            attributes=settings.BLEACH_ALLOWED_ATTRIBUTES,
            protocols=settings.BLEACH_ALLOWED_PROTOCOLS,
            css_sanitizer=_CSS_SANITIZER,
            strip=True,
        )
