from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from urllib.parse import urlencode
import re

from accounts.models import Profile

from .forms import CategoryForm, PostEditForm, PostForm, TagForm
from .models import Category, Collection, Comment, Like, Post, SearchLog, Tag


@login_required(login_url=settings.LOGIN_URL)
def feed(request):
    search_query = (request.GET.get("q") or "").strip()
    category_id = (request.GET.get("category") or "").strip()
    tag_id = (request.GET.get("tag") or "").strip()

    if request.method == "POST":
        # Use the edit form for creation too, so users can add new category/tags inline.
        form = PostEditForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.instance = post
            form.save_m2m()

            new_tags_raw = (form.cleaned_data.get("new_tags") or "").strip()
            if new_tags_raw:
                names = [p.strip() for p in re.split(r"[,\s]+", new_tags_raw) if p.strip()]
                seen = set()
                uniq = []
                for name in names:
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    uniq.append(name)
                tag_objs = [Tag.objects.get_or_create(name=n)[0] for n in uniq]
                post.tags.add(*tag_objs)
            messages.success(request, "已發布貼文。")
            return redirect("posts:feed")
    else:
        form = PostEditForm()

    posts = (
        Post.objects.select_related("author", "author__profile", "category")
        .prefetch_related("likes", "comments", "tags")
    )
    if search_query:
        posts = posts.filter(
            Q(content__icontains=search_query) | Q(author__username__icontains=search_query)
        )
        SearchLog.objects.create(user=request.user, keyword=search_query)

    if category_id.isdigit():
        posts = posts.filter(category_id=int(category_id))
    if tag_id.isdigit():
        posts = posts.filter(tags__id=int(tag_id))
    posts = posts.all()

    author_ids = set(posts.values_list("author_id", flat=True))
    existing_profile_ids = set(Profile.objects.filter(user_id__in=author_ids).values_list("user_id", flat=True))
    missing_profile_ids = author_ids - existing_profile_ids
    if missing_profile_ids:
        Profile.objects.bulk_create([Profile(user_id=user_id) for user_id in missing_profile_ids], ignore_conflicts=True)
        posts = (
            Post.objects.select_related("author", "author__profile", "category")
            .prefetch_related("likes", "comments", "tags")
        )
        if search_query:
            posts = posts.filter(
                Q(content__icontains=search_query) | Q(author__username__icontains=search_query)
            )
        if category_id.isdigit():
            posts = posts.filter(category_id=int(category_id))
        if tag_id.isdigit():
            posts = posts.filter(tags__id=int(tag_id))
        posts = posts.all()

    return render(
        request,
        "posts/feed.html",
        {
            "posts": posts,
            "form": form,
            "search_query": search_query,
            "results_count": posts.count(),
            "categories": Category.objects.all(),
            "tags": Tag.objects.all(),
            "selected_category": category_id,
            "selected_tag": tag_id,
        },
    )


@login_required(login_url=settings.LOGIN_URL)
def like_toggle(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like = post.likes.filter(user=request.user).first()
    if like:
        like.delete()
        messages.info(request, "已取消按讚。")
    else:
        Like.objects.get_or_create(user=request.user, post=post)
        messages.success(request, "已按讚。")
    search_query = (request.GET.get("q") or "").strip()
    if search_query:
        feed_url = reverse("posts:feed")
        return redirect(f"{feed_url}?{urlencode({'q': search_query})}")
    return redirect("posts:feed")


@login_required(login_url=settings.LOGIN_URL)
def collect_toggle(request, pk):
    post = get_object_or_404(Post, pk=pk)
    collection = post.collections.filter(user=request.user).first()
    if collection:
        collection.delete()
        messages.info(request, "已取消收藏。")
    else:
        Collection.objects.get_or_create(user=request.user, post=post)
        messages.success(request, "已收藏貼文。")
    return redirect(request.META.get("HTTP_REFERER") or "posts:feed")


@login_required(login_url=settings.LOGIN_URL)
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method != "POST":
        return redirect("posts:feed")
    content = (request.POST.get("content") or "").strip()
    if content:
        Comment.objects.create(post=post, author=request.user, content=content)
        messages.success(request, "留言已送出。")
    search_query = (request.POST.get("q") or "").strip()
    if search_query:
        feed_url = reverse("posts:feed")
        return redirect(f"{feed_url}?{urlencode({'q': search_query})}")
    return redirect("posts:feed")


def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("author", "author__profile", "category").prefetch_related("tags", "comments", "likes"),
        pk=pk,
    )
    is_liked = False
    is_collected = False
    if request.user.is_authenticated:
        is_liked = post.likes.filter(user=request.user).exists()
        is_collected = post.collections.filter(user=request.user).exists()
    return render(
        request,
        "posts/post_detail.html",
        {"post": post, "is_liked": is_liked, "is_collected": is_collected},
    )


@login_required(login_url=settings.LOGIN_URL)
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == "POST":
        form = PostEditForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "貼文已更新。")
            return redirect("posts:post_detail", pk=post.pk)
    else:
        form = PostEditForm(instance=post)
    return render(request, "posts/post_edit.html", {"form": form, "post": post})


@login_required(login_url=settings.LOGIN_URL)
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == "POST":
        post.delete()
        messages.success(request, "貼文已刪除。")
        return redirect("posts:feed")
    return render(request, "posts/post_confirm_delete.html", {"post": post})


def _staff_required(request):
    if not request.user.is_authenticated:
        return redirect(settings.LOGIN_URL)
    if not request.user.is_staff:
        messages.error(request, "需要管理員權限才能操作。")
        return redirect("posts:feed")
    return None


def category_manage(request):
    blocked = _staff_required(request)
    if blocked is not None:
        return blocked

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "已新增分類。")
            return redirect("posts:category_manage")
    else:
        form = CategoryForm()
    categories = Category.objects.order_by("name")
    return render(request, "posts/category_manage.html", {"form": form, "categories": categories})


def category_delete(request, pk):
    blocked = _staff_required(request)
    if blocked is not None:
        return blocked
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.delete()
        messages.success(request, "已刪除分類。")
    return redirect("posts:category_manage")


def tag_manage(request):
    blocked = _staff_required(request)
    if blocked is not None:
        return blocked

    if request.method == "POST":
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "已新增標籤。")
            return redirect("posts:tag_manage")
    else:
        form = TagForm()
    tags = Tag.objects.order_by("name")
    return render(request, "posts/tag_manage.html", {"form": form, "tags": tags})


def tag_delete(request, pk):
    blocked = _staff_required(request)
    if blocked is not None:
        return blocked
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == "POST":
        tag.delete()
        messages.success(request, "已刪除標籤。")
    return redirect("posts:tag_manage")


@login_required(login_url=settings.LOGIN_URL)
def collections_list(request):
    collections = (
        Collection.objects.filter(user=request.user)
        .select_related("post", "post__author", "post__author__profile", "post__category")
        .prefetch_related("post__tags")
        .order_by("-created_at")
    )
    posts = [c.post for c in collections]
    return render(request, "posts/collections.html", {"posts": posts, "collections_count": len(posts)})
