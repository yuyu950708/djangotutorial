from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile

from .forms import PostForm
from .models import Comment, Like, Post


@login_required(login_url=settings.LOGIN_URL)
def feed(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("posts:feed")
    else:
        form = PostForm()

    posts = Post.objects.select_related("author", "author__profile").prefetch_related("likes", "comments").all()
    author_ids = set(posts.values_list("author_id", flat=True))
    existing_profile_ids = set(Profile.objects.filter(user_id__in=author_ids).values_list("user_id", flat=True))
    missing_profile_ids = author_ids - existing_profile_ids
    if missing_profile_ids:
        Profile.objects.bulk_create([Profile(user_id=user_id) for user_id in missing_profile_ids], ignore_conflicts=True)
        posts = Post.objects.select_related("author", "author__profile").prefetch_related("likes", "comments").all()
    return render(request, "posts/feed.html", {"posts": posts, "form": form})


@login_required(login_url=settings.LOGIN_URL)
def like_toggle(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like = post.likes.filter(user=request.user).first()
    if like:
        like.delete()
    else:
        Like.objects.get_or_create(user=request.user, post=post)
    return redirect("posts:feed")


@login_required(login_url=settings.LOGIN_URL)
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method != "POST":
        return redirect("posts:feed")
    content = (request.POST.get("content") or "").strip()
    if content:
        Comment.objects.create(post=post, author=request.user, content=content)
    return redirect("posts:feed")


def post_detail(request, pk):
    return HttpResponse(f"Post detail {pk} (to be implemented)")
