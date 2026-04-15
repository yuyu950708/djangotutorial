import json
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode

from accounts.models import Profile

from .ai_chat import get_assistant_reply
from .forms import CategoryForm, PostEditForm, PostForm, TagForm
from .models import Category, Collection, Comment, Like, Post, SearchLog, Tag


def feed(request):
    search_query = (request.GET.get("q") or "").strip()
    category_id = (request.GET.get("category") or "").strip()
    tag_id = (request.GET.get("tag") or "").strip()
    page_number = (request.GET.get("page") or "").strip()

    if len(search_query) > 100:
        search_query = search_query[:100]
        messages.info(request, "搜尋字數過長，已自動截斷。")

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?{urlencode({'next': request.get_full_path()})}")

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
        .annotate(comment_count=Count("comments", distinct=True))
    )
    if search_query:
        posts = posts.filter(
            Q(content__icontains=search_query) | Q(author__username__icontains=search_query)
        )
        if request.user.is_authenticated:
            last = (
                SearchLog.objects.filter(user=request.user, keyword=search_query)
                .order_by("-created_at")
                .first()
            )
            if last is None or last.created_at < timezone.now() - timedelta(seconds=30):
                SearchLog.objects.create(user=request.user, keyword=search_query)

    if category_id.isdigit():
        posts = posts.filter(category_id=int(category_id))
    if tag_id.isdigit():
        posts = posts.filter(tags__id=int(tag_id)).distinct()
    posts = posts.all()

    author_ids = set(posts.values_list("author_id", flat=True))
    existing_profile_ids = set(Profile.objects.filter(user_id__in=author_ids).values_list("user_id", flat=True))
    missing_profile_ids = author_ids - existing_profile_ids
    if missing_profile_ids:
        Profile.objects.bulk_create([Profile(user_id=user_id) for user_id in missing_profile_ids], ignore_conflicts=True)
        posts = (
            Post.objects.select_related("author", "author__profile", "category")
            .prefetch_related("likes", "comments", "tags")
            .annotate(comment_count=Count("comments", distinct=True))
        )
        if search_query:
            posts = posts.filter(
                Q(content__icontains=search_query) | Q(author__username__icontains=search_query)
            )
        if category_id.isdigit():
            posts = posts.filter(category_id=int(category_id))
        if tag_id.isdigit():
            posts = posts.filter(tags__id=int(tag_id)).distinct()
        posts = posts.all()

    paginator = Paginator(posts, 20)
    page_obj = paginator.get_page(page_number or 1)

    return render(
        request,
        "posts/feed.html",
        {
            "posts": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "form": form,
            "search_query": search_query,
            "results_count": paginator.count,
            "categories": Category.objects.all(),
            "tags": Tag.objects.all(),
            "selected_category": category_id,
            "selected_tag": tag_id,
        },
    )


@login_required(login_url=settings.LOGIN_URL)
def like_toggle(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method != "POST":
        return redirect("posts:feed")
    like = post.likes.filter(user=request.user).first()
    if like:
        like.delete()
        messages.info(request, "已取消按讚。")
    else:
        Like.objects.get_or_create(user=request.user, post=post)
        messages.success(request, "已按讚。")
    next_url = (request.POST.get("next") or "").strip()
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("posts:feed")


@login_required(login_url=settings.LOGIN_URL)
def collect_toggle(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method != "POST":
        return redirect("posts:feed")
    collection = post.collections.filter(user=request.user).first()
    if collection:
        collection.delete()
        messages.info(request, "已取消收藏。")
    else:
        Collection.objects.get_or_create(user=request.user, post=post)
        messages.success(request, "已收藏貼文。")
    next_url = (request.POST.get("next") or "").strip()
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("posts:feed")


@login_required(login_url=settings.LOGIN_URL)
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method != "POST":
        return redirect("posts:feed")
    content = (request.POST.get("content") or "").strip()
    if len(content) > 500:
        content = content[:500]
    if content:
        Comment.objects.create(post=post, author=request.user, content=content)
        messages.success(request, "留言已送出。")
    else:
        messages.error(request, "留言內容不可為空。")
    next_url = (request.POST.get("next") or "").strip()
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
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
    paginator = Paginator(posts, 20)
    page_obj = paginator.get_page((request.GET.get("page") or "").strip() or 1)
    return render(
        request,
        "posts/collections.html",
        {
            "posts": page_obj.object_list,
            "collections_count": paginator.count,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )


@require_POST
def ai_chat(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "請先登入後再使用 AI 小幫手。"}, status=401)
    message = (request.POST.get("message") or "").strip()[:4000]
    image = request.FILES.get("image")
    history_raw = request.POST.get("history") or "[]"
    try:
        history = json.loads(history_raw)
    except json.JSONDecodeError:
        history = []

    if image and image.size > 5 * 1024 * 1024:
        return JsonResponse({"error": "圖片請小於 5MB。"}, status=400)
    if image:
        ct = (getattr(image, "content_type", "") or "").lower()
        if ct and ct not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            return JsonResponse({"error": "請上傳 JPG、PNG、GIF 或 WebP 圖片。"}, status=400)
    if not message and not image:
        return JsonResponse({"error": "請輸入文字或上傳圖片。"}, status=400)

    reply = get_assistant_reply(message=message, image=image, history=history)
    return JsonResponse({"reply": reply})
