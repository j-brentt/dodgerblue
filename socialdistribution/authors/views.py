from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.urls import reverse, NoReverseMatch
from .models import Author, FollowRequest, FollowRequestStatus
from entries.models import Entry, Visibility
from .forms import ProfileEditForm

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
        
        # Check if username exists
        if Author.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'authors/signup.html')
        
        # Create the author (not approved by default)
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
    Only the author themselves can edit their profile.
    ***still need to add description***
    """
    author = get_object_or_404(Author, id=author_id)
    
    # Ensure the logged-in user can only edit their own profile
    # Since Author extends AbstractUser, request.user IS the author
    if request.user.id != author.id:
        messages.error(request, "You can only edit your own profile.")
        return redirect('authors:stream')
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST)
        if form.is_valid():
            # Manually save the form data to the author
            author.display_name = form.cleaned_data['display_name']
            author.github = form.cleaned_data['github']
            author.profile_image = form.cleaned_data['profile_image']
            author.save()
            
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('authors:stream') 
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
    Display the main feed/stream for the logged-in author.    
    """
    author = request.user  
    entries = (
        Entry.objects
        .filter(
            Q(visibility=Visibility.PUBLIC) | Q(author=author)
        )
        .select_related("author")
        .order_by("-published")
    )
    context = {
        'author': author,
        'entries': entries,
        'pending_follow_requests_count': author.follow_requests_received.filter(
            status=FollowRequestStatus.PENDING
        ).count(),
    }
    
    return render(request, 'authors/stream.html', context)

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
            return_url = reverse("authors:stream")  # Takes the user back to the previous page
        except NoReverseMatch:
            return_url = "/"

    follow_relationship = None
    if request.user.is_authenticated and request.user != profile_author:
        follow_relationship = (
            FollowRequest.objects.filter(follower=request.user, followee=profile_author)
            .select_related("follower", "followee")
            .first()
        )

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
