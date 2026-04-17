from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.views import (
    LoginView as DjangoLoginView,
    LogoutView as DjangoLogoutView,
)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileEditForm, RegisterForm, UsernameOrEmailAuthenticationForm
from .models import Profile

from posts.models import Follow, Post, PostComment

User = get_user_model()


class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    authentication_form = UsernameOrEmailAuthenticationForm


class LogoutView(DjangoLogoutView):
    next_page = "accounts:login"


def register(request):
    if request.user.is_authenticated:
        return redirect("posts:feed")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            return redirect("posts:feed")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def profile_edit(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile_detail", username=request.user.username)
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, "accounts/profile_edit.html", {"form": form})


def profile_detail(request, username):
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)
    posts = Post.objects.filter(author=user).order_by("-created_at")[:20]
    recent_comments = (
        PostComment.objects.filter(author=user)
        .select_related("post")
        .order_by("-created_at")[:20]
    )
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(follower=request.user, following=user).exists()
    return render(
        request,
        "accounts/profile_detail.html",
        {
            "profile_user": user,
            "profile": profile,
            "posts": posts,
            "recent_comments": recent_comments,
            "is_following": is_following,
        },
    )


@login_required(login_url="accounts:login")
def follow_toggle(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        messages.error(request, "不能追蹤自己。")
        return redirect("accounts:profile_detail", username=target.username)

    relation = Follow.objects.filter(follower=request.user, following=target).first()
    if relation:
        relation.delete()
        messages.info(request, "已取消追蹤。")
    else:
        Follow.objects.get_or_create(follower=request.user, following=target)
        messages.success(request, "已追蹤。")
    return redirect("accounts:profile_detail", username=target.username)
