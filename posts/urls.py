from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("collections/", views.collections_list, name="collections_list"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("<int:pk>/edit/", views.post_edit, name="post_edit"),
    path("<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("<int:pk>/like-toggle/", views.like_toggle, name="like_toggle"),
    path("<int:pk>/collect-toggle/", views.collect_toggle, name="collect_toggle"),
    path("<int:pk>/comment/", views.comment_create, name="comment_create"),
    path("categories/", views.category_manage, name="category_manage"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("tags/", views.tag_manage, name="tag_manage"),
    path("tags/<int:pk>/delete/", views.tag_delete, name="tag_delete"),
]

