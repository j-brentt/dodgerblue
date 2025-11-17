from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse, HttpResponse
from django.core.files.storage import default_storage
from .models import Entry, Visibility, Comment
from .forms import EntryForm, CommentForm
import uuid
import base64
from django.conf import settings
from django.urls import reverse
from .api_views import send_entry_to_remote_followers


class PublicEntriesListView(ListView):
    model = Entry
    template_name = "entries/view_entry.html"  # consider making a list template, e.g., entries/public_list.html
    context_object_name = "entries"

    def get_template_names(self):
        return ["entries/public_list.html"] if self.request else [self.template_name]

    def get_queryset(self):
        return (
            Entry.objects
            .filter(visibility=Visibility.PUBLIC)
            .select_related("author")
            .order_by("-published")
        )

@login_required
def create_entry(request):
    """Create a new entry"""
    if request.method == 'POST':
        form = EntryForm(request.POST, request.FILES)
        if form.is_valid():
            content_type = form.cleaned_data['content_type']
            # Handle image entries
            if content_type.startswith('image'):
                image_file = form.cleaned_data['image']
                mime = image_file.content_type
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
                content = image_data
                content_type = f"{mime};base64"
            else:
                # Handle text entries
                content = form.cleaned_data['content']
            # Create the entry
            entry = Entry.objects.create(
                author=request.user,
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                content=content,
                content_type=content_type,
                visibility=form.cleaned_data['visibility']
            )

            send_entry_to_remote_followers(entry, request)

            messages.success(request, 'Entry created successfully!')
            return redirect('entries:view_entry', entry_id=entry.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EntryForm()
    
    context = {'form': form}
    return render(request, 'entries/create_entry.html', context)

@login_required
def edit_entry(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id)

    if request.user != entry.author:
        messages.error(request, "You can only edit your own entries.")
        return redirect('authors:stream')

    if entry.visibility == 'DELETED':
        messages.error(request, "Cannot edit deleted entries.")
        return redirect('authors:stream')

    if request.method == 'POST':
        form = EntryForm(request.POST, request.FILES, initial={'content': entry.content, 'is_new': False})
        if form.is_valid():
            content_type = form.cleaned_data['content_type']

            # handle images
            if content_type in ['image/png;base64', 'image/jpeg;base64']:
                image_file = form.cleaned_data.get('image')
                if image_file:
                    import base64
                    entry.content = base64.b64encode(image_file.read()).decode('utf-8')
                    entry.content_type = f"{image_file.content_type};base64"

            # handle text or markdown
            elif content_type.startswith('text'):
                entry.content = form.cleaned_data['content']

                # preserve markdown if it was markdown before
                if entry.content_type == 'text/markdown' or content_type == 'text/markdown':
                    entry.content_type = 'text/markdown'
                else:
                    entry.content_type = 'text/plain'

            entry.title = form.cleaned_data['title']
            entry.description = form.cleaned_data['description']
            entry.visibility = form.cleaned_data['visibility']
            entry.save()

            send_entry_to_remote_followers(entry, request)
            
            messages.success(request, 'Entry updated successfully!')
            return redirect('entries:view_entry', entry_id=entry.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EntryForm(initial={
            'title': entry.title,
            'description': entry.description,
            'content_type': entry.content_type,
            'content': entry.content if entry.content_type.startswith('text') else '',
            'visibility': entry.visibility,
        })

    return render(request, 'entries/edit_entry.html', {'form': form, 'entry': entry})

@login_required
def delete_entry(request, entry_id):
    """Delete an entry (mark as DELETED)"""
    # Convert string ID to UUID
    try:
        entry_id_uuid = entry_id
    except ValueError:
        messages.error(request, "Invalid entry ID.")
        return redirect('authors:stream')
    
    entry = get_object_or_404(Entry, id=entry_id_uuid)
    
    if request.user.id != entry.author.id:
        messages.error(request, "You can only delete your own entries.")
        return redirect('authors:stream')
    
    if request.method == 'POST':
        # Mark as deleted (dont remove from database)
        entry.visibility = 'DELETED'
        entry.save()
        send_entry_to_remote_followers(entry, request)
        
        messages.success(request, 'Entry deleted successfully!')
        return redirect('authors:stream')
    
    context = {'entry': entry}
    return render(request, 'entries/delete_entry.html', context)


# @login_required  - removing this for now as public entries need to be viewable by all users (i.e. anonymous too)
def view_entry(request, entry_id):
    """View a single entry by UUID with visibility enforcement."""
    # Convert string ID to UUID
    try:
        entry_uuid = uuid.UUID(str(entry_id))
    except (ValueError, TypeError):
        raise Http404("Invalid entry ID")

    entry = get_object_or_404(Entry, id=entry_uuid)
    liked_users = entry.liked_by.all()

    if entry.content_type.startswith("image/"):
        image_url = request.build_absolute_uri(
            reverse("entries:entry_image", args=[entry.author.id, entry.id])
        )
    else:
        image_url = None

    # Deleted entries hidden from non-staff
    if entry.visibility == "DELETED" and not request.user.is_staff:
        raise Http404("Entry not found")

    # Check if user has correct permission to view
    if not entry.can_view(request.user):
        raise PermissionDenied

    comments = entry.comments.select_related("author")
    if (
        entry.visibility == Visibility.FRIENDS
        and request.user.is_authenticated
        and request.user != entry.author
    ):
        comments = comments.filter(author__in=[request.user, entry.author])
    comment_form = CommentForm()

    context = {
        "entry": entry,
        "liked_users": liked_users,
        "comments": comments,
        "comment_form": comment_form,
        "is_friend_view": (
            entry.visibility == Visibility.FRIENDS
            and request.user.is_authenticated
            and request.user != entry.author
        ),
        "image_url": image_url,
    }
    return render(request, "entries/view_entry.html", context)



def entry_image(request, author_id, entry_id):
    """Return the raw image data for an image-type entry so it can be embedded."""
    entry = get_object_or_404(Entry, id=entry_id, author_id=author_id)

    # Only serve actual image posts
    if not entry.content_type.startswith("image/"):
        raise Http404("This entry is not an image.")

    # Decode the stored base64 image data
    image_data = base64.b64decode(entry.content)
    mime_type = entry.content_type.split(";")[0]  # e.g. "image/png"

    return HttpResponse(image_data, content_type=mime_type)


@login_required
@require_POST
def like_entry(request, entry_id):
    try:
        entry_uuid = uuid.UUID(str(entry_id))
    except (ValueError, TypeError):
        raise Http404("Invalid entry ID")

    entry = get_object_or_404(Entry, id=entry_uuid)

    if not entry.can_view(request.user):
        raise PermissionDenied

    entry.liked_by.add(request.user)

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return redirect(next_url)
    return redirect("entries:view_entry", entry_id=entry.id)


@login_required
@require_POST
def add_comment(request, entry_id):
    try:
        entry_uuid = uuid.UUID(str(entry_id))
    except (ValueError, TypeError):
        raise Http404("Invalid entry ID")

    entry = get_object_or_404(Entry, id=entry_uuid)

    if not entry.can_view(request.user):
        raise PermissionDenied

    form = CommentForm(request.POST)
    if form.is_valid():
        Comment.objects.create(
            entry=entry,
            author=request.user,
            content=form.cleaned_data["content"],
        )
        messages.success(request, "Comment posted.")
    else:
        messages.error(request, "Please correct the comment and try again.")

    return redirect("entries:view_entry", entry_id=entry.id)


@login_required
@require_POST
def like_comment(request, comment_id):
    try:
        comment_uuid = uuid.UUID(str(comment_id))
    except (ValueError, TypeError):
        raise Http404("Invalid comment ID")

    comment = get_object_or_404(
        Comment.objects.select_related("entry"),
        id=comment_uuid,
    )

    if not comment.entry.can_view(request.user):
        raise PermissionDenied

    if (
        comment.entry.visibility == Visibility.FRIENDS
        and request.user not in {comment.entry.author, comment.author}
    ):
        raise PermissionDenied

    comment.liked_by.add(request.user)
    messages.success(request, "Comment liked.")
    return redirect("entries:view_entry", entry_id=comment.entry.id)


@login_required
def my_entries(request):
    """List all of the users entires"""
    entries = Entry.objects.filter(author=request.user).exclude(visibility='DELETED').order_by('-published')
    context = {'entries': entries}
    return render(request, 'entries/my_entries.html', context)

@login_required
def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        image_path = default_storage.save(f'uploads/{image_file.name}', image_file)
        image_url = request.build_absolute_uri(settings.MEDIA_URL + image_path)
        return JsonResponse({'url': image_url})
    return JsonResponse({'error': 'No image provided'}, status=400)
