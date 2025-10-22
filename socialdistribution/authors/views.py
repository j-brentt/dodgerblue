from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.urls import reverse, NoReverseMatch
from .models import Author, FollowRequest, FollowRequestStatus
from entries.models import Entry, Visibility
from .forms import ProfileEditForm
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import AuthorSerializer

def signup(request):
    """Handle user registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        display_name = request.POST.get('display_name')
        
        # Validation
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'authors/signup.html')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'authors/signup.html')
        
        # Check if username exists (prevents duplicate usernames login)
        if Author.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'authors/signup.html')
        
        # Create the author account (requires admin approval before )
        author = Author.objects.create_user(
            username=username,
            email=email,
            password=password,
            display_name=display_name or username,
            is_approved=False  # Requires admin approval
        )
        
        messages.success(request, 'Account created! Please wait for admin approval before logging in.')
        return redirect('authors:login')
    
    return render(request, 'authors/signup.html')

@login_required
def profile_edit(request, author_id):
    """
    View for editing an author's profile.
    Only the currently logged-in author can access this page.
    ***still need to add description***
    """
    author = get_object_or_404(Author, id=author_id)
    
    # Block users from editing others profile
    if request.user.id != author.id:
        messages.error(request, "You can only edit your own profile.")
        return redirect('stream')
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST)
        if form.is_valid():
            # Manually save the form data to the author
            author.display_name = form.cleaned_data['display_name']
            author.github = form.cleaned_data['github']
            author.profile_image = form.cleaned_data['profile_image']
            author.save()
            
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('stream') 
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-populate form with current author data
        form = ProfileEditForm(initial={
            'display_name': author.display_name,
            'github': author.github,
            'profile_image': author.profile_image,
        })
    
    context = {
        'author': author,
        'form': form
    }
    return render(request, 'authors/profile_edit.html', context)

@login_required
def stream(request):
    """
    Show the main feed for the logged-in author.
    Displays publuc posts and user's own posts.    
    """
    author = request.user 

    # Get candidate entries: all public, friends, unlisted, or own
    following_authors = author.follow_requests_sent.filter(
        status=FollowRequestStatus.APPROVED
    ).values_list("followee", flat=True)

    candidate_entries = Entry.objects.filter(
        Q(visibility=Visibility.PUBLIC) |
        Q(author=author) |
        Q(author__in=following_authors) |
        Q(visibility=Visibility.UNLISTED)
    ).select_related("author").order_by("-published")

    # Filter using can_view
    entries = [entry for entry in candidate_entries if entry.can_view(author)]

    context = {
        "author": author,
        "entries": entries,
        "pending_follow_requests_count": author.follow_requests_received.filter(
            status=FollowRequestStatus.PENDING
        ).count(),
    }

    return render(request, "authors/stream.html", context)

# Contains the info for a users profile page
def profile_detail(request, author_id):
    profile_author = get_object_or_404(Author, id=author_id)
    entries = (
        profile_author.entries.filter(visibility=Visibility.PUBLIC)
        .select_related("author")
        .order_by("-published")
    )
    return_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if not return_url:
        try:
            return_url = reverse("stream")  # Takes the user back to the previous page
        except NoReverseMatch:
            return_url = "/"

    follow_relationship = None
    if request.user.is_authenticated and request.user != profile_author:
        follow_relationship = (
            FollowRequest.objects.filter(follower=request.user, followee=profile_author)
            .select_related("follower", "followee")
            .first()
        )
    friends_count = profile_author.get_friends_count()
    context = {
        "profile_author": profile_author,
        "entries": entries,
        "return_url": return_url,
        "follow_relationship": follow_relationship,
        "followers_count": profile_author.follow_requests_received.filter(
            status=FollowRequestStatus.APPROVED
        ).count(),
        "following_count": profile_author.follow_requests_sent.filter(
            status=FollowRequestStatus.APPROVED
        ).count(),
        "friends_count": friends_count,
    }
    return render(request, "authors/profile_detail.html", context)

@login_required
def send_follow_request(request, author_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    followee = get_object_or_404(Author, id=author_id)

    if followee == request.user:
        messages.error(request, "You cannot follow yourself.")
        return redirect(followee.get_absolute_url())

    follow_request, created = FollowRequest.objects.get_or_create(
        follower=request.user,
        followee=followee,
        defaults={"status": FollowRequestStatus.PENDING},
    )

    if created:
        messages.success(request, f"Follow request sent to {followee.display_name}.")
    else:
        if follow_request.status == FollowRequestStatus.APPROVED:
            messages.info(request, f"You already follow {followee.display_name}.")
        elif follow_request.status == FollowRequestStatus.PENDING:
            messages.info(
                request, f"Your follow request to {followee.display_name} is pending approval."
            )
        else:
            follow_request.status = FollowRequestStatus.PENDING
            follow_request.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Follow request re-sent to {followee.display_name}.")

    return redirect(followee.get_absolute_url())


@login_required
def unfollow_author(request, author_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    followee = get_object_or_404(Author, id=author_id)
    follow_request = get_object_or_404(
        FollowRequest,
        follower=request.user,
        followee=followee,
        status=FollowRequestStatus.APPROVED,
    )
    follow_request.delete()
    messages.info(request, f"You unfollowed {followee.display_name}.")
    return redirect(followee.get_absolute_url())


@login_required
def follow_requests(request):
    incoming_pending = (
        request.user.follow_requests_received.filter(status=FollowRequestStatus.PENDING)
        .select_related("follower")
        .order_by("created_at")
    )
    incoming_recent = (
        request.user.follow_requests_received.filter(status=FollowRequestStatus.APPROVED)
        .select_related("follower")
        .order_by("-updated_at")[:10]
    )
    outgoing_pending = (
        request.user.follow_requests_sent.filter(status=FollowRequestStatus.PENDING)
        .select_related("followee")
        .order_by("created_at")
    )

    context = {
        "incoming_pending": incoming_pending,
        "incoming_recent": incoming_recent,
        "outgoing_pending": outgoing_pending,
    }
    return render(request, "authors/follow_requests.html", context)


@login_required
def approve_follow_request(request, request_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    follow_request = get_object_or_404(
        FollowRequest.objects.select_related("follower", "followee"),
        id=request_id,
        followee=request.user,
    )
    follow_request.approve()
    messages.success(
        request, f"You approved {follow_request.follower.display_name}'s follow request."
    )
    return redirect("authors:follow_requests")


@login_required
def deny_follow_request(request, request_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    follow_request = get_object_or_404(
        FollowRequest.objects.select_related("follower", "followee"),
        id=request_id,
        followee=request.user,
    )
    follow_request.reject()
    messages.info(
        request, f"You denied {follow_request.follower.display_name}'s follow request."
    )
    return redirect("authors:follow_requests")

@login_required
def followers_list(request, author_id):
    """
    Creates a list of the users followers
    """
    profile_author = get_object_or_404(Author, id=author_id)
    users = Author.objects.filter(
        follow_requests_sent__followee=profile_author,
        follow_requests_sent__status=FollowRequestStatus.APPROVED
    ).distinct()
    return render(request, "authors/followers_list.html", {
        "users": users,
        "profile_author": profile_author,
        "title": f"{profile_author.display_name}'s Followers",
    })
@login_required
def following_list(request, author_id):
    """
    Creates a list of people the user follows
    """
    profile_author = get_object_or_404(Author, id=author_id)
    users = Author.objects.filter(
        follow_requests_received__follower=profile_author,
        follow_requests_received__status=FollowRequestStatus.APPROVED
    ).distinct()
    return render(request, "authors/following_list.html", {
        "users": users,
        "profile_author": profile_author,
        "title": f"{profile_author.display_name} Follows",
    })


@login_required
def friends_list(request, author_id):
    """
    Creates a list of ussers friends (mutual following)
    """
    profile_author = get_object_or_404(Author, id=author_id)
    users = Author.objects.filter(
        follow_requests_sent__status=FollowRequestStatus.APPROVED,
        follow_requests_sent__followee__follow_requests_sent__follower=profile_author,
        follow_requests_sent__followee__follow_requests_sent__status=FollowRequestStatus.APPROVED,
    ).distinct()
    return render(request, "authors/friends_list.html", {
        "users": users,
        "profile_author": profile_author,
        "title": f"{profile_author.display_name}'s Friends",
    })
