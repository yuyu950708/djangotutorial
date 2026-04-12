import bleach
import re
from bleach.css_sanitizer import ALLOWED_CSS_PROPERTIES, CSSSanitizer
from django import forms
from django.conf import settings
from django.utils.html import strip_tags

from .models import Category, Post, Tag
from .models import Category, Tag

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
            tags=getattr(settings, "BLEACH_ALLOWED_TAGS", None),
            attributes=getattr(settings, "BLEACH_ALLOWED_ATTRIBUTES", None),
            protocols=getattr(settings, "BLEACH_ALLOWED_PROTOCOLS", None),
            css_sanitizer=_CSS_SANITIZER,
            strip=True,
        )


class PostEditForm(PostForm):
    new_category = forms.CharField(
        required=False,
        label="新增分類",
        widget=forms.TextInput(
            attrs={
                "class": "min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base outline-none ring-sky-200 focus:ring sm:text-sm",
                "placeholder": "想不到分類？直接輸入新增",
            }
        ),
    )
    new_tags = forms.CharField(
        required=False,
        label="新增標籤",
        widget=forms.TextInput(
            attrs={
                "class": "min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base outline-none ring-sky-200 focus:ring sm:text-sm",
                "placeholder": "用逗號或空格分隔，例如：辣, 便宜",
            }
        ),
        help_text="可輸入多個，逗號或空格分隔",
    )

    class Meta:
        model = Post
        fields = ("title", "category", "tags", "content", "image")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base outline-none ring-sky-200 focus:ring sm:text-sm",
                    "placeholder": "標題（可留空）",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base outline-none ring-sky-200 focus:ring sm:text-sm",
                }
            ),
            "tags": forms.SelectMultiple(
                attrs={
                    "class": "min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base outline-none ring-sky-200 focus:ring sm:text-sm",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "block w-full cursor-pointer rounded-lg border border-slate-300 text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-slate-700 hover:file:bg-slate-200",
                }
            ),
        }

    def clean_new_category(self):
        value = (self.cleaned_data.get("new_category") or "").strip()
        return value

    def clean_new_tags(self):
        value = (self.cleaned_data.get("new_tags") or "").strip()
        return value

    def _parse_new_tags(self, raw: str):
        # Split by comma/whitespace and keep unique order.
        parts = [p.strip() for p in re.split(r"[,\s]+", raw) if p.strip()]
        seen = set()
        out = []
        for p in parts:
            key = p.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    def save(self, commit=True):
        post = super().save(commit=False)

        new_category = self.cleaned_data.get("new_category") or ""
        if new_category:
            category_obj, _ = Category.objects.get_or_create(name=new_category)
            post.category = category_obj

        if commit:
            post.save()
            self.save_m2m()

            new_tags_raw = self.cleaned_data.get("new_tags") or ""
            if new_tags_raw:
                tag_names = self._parse_new_tags(new_tags_raw)
                tag_objs = [Tag.objects.get_or_create(name=name)[0] for name in tag_names]
                post.tags.add(*tag_objs)

        return post


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base outline-none ring-sky-200 focus:ring sm:text-sm",
                    "placeholder": "例如：中式",
                }
            )
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base outline-none ring-sky-200 focus:ring sm:text-sm",
                    "placeholder": "例如：健康",
                }
            )
        }
