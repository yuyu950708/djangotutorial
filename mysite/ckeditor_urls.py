"""
CKEditor 上傳／瀏覽：套件預設為 staff 專用，改為「已登入會員」即可使用。
"""
from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.decorators.cache import never_cache

from ckeditor_uploader import views as ckeditor_views

urlpatterns = [
    re_path(
        r"^upload/",
        login_required(ckeditor_views.upload),
        name="ckeditor_upload",
    ),
    re_path(
        r"^browse/",
        never_cache(login_required(ckeditor_views.browse)),
        name="ckeditor_browse",
    ),
]
