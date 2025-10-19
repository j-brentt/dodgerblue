from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from django.http import Http404
from .models import Entry, Visibility
from .forms import EntryForm
import uuid
import base64

class PublicEntriesListView(ListView):
    model = Entry
    template_name = "entries/view_entry.html"  # consider making a list template, e.g., entries/public_list.html
    context_object_name = "entries"

    def get_template_names(self):
        # Prefer a list template if you have one
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
            if content_type in ['image/png;base64', 'image/jpeg;base64']:
                image_file = form.cleaned_data['image']
                # Convert image to base64
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
                content = image_data
            else:
                # Handle text entries
                content = form.cleaned_data['content']
            # Create the entry
            entry = Entry.objects.create(
                author=request.user,
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                content=content,
                content_type=form.cleaned_data['content_type'],
                visibility=form.cleaned_data['visibility']
            )
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
    # Cannot view others entires
    if request.user != entry.author:
        messages.error(request, "You can only edit your own entries.")
        return redirect('authors:stream')
    # Cannot edit deleted entries
    if entry.visibility == 'DELETED':
        messages.error(request, "Cannot edit deleted entries.")
        return redirect('authors:stream')
    
    if request.method == 'POST':
        #  When submitting the form, we pass request.FILES for file uploads (images)
        # Also set 'initial' here to provide the existing content to the form,
        form = EntryForm(request.POST, request.FILES, initial={'content': entry.content, 'is_new': False})
        if form.is_valid():
            content_type = form.cleaned_data['content_type']
             # Handles images separately
            if content_type in ['image/png;base64', 'image/jpeg;base64']:
                image_file = form.cleaned_data.get('image')
                # Converts and stores uploaded images to base64
                if image_file:
                    import base64
                    entry.content = base64.b64encode(image_file.read()).decode('utf-8')
                    entry.content_type = f"{image_file.content_type};base64"
            else:
                # Simply saves the text content
                entry.content = form.cleaned_data['content']
                entry.content_type = content_type

            entry.title = form.cleaned_data['title']
            entry.description = form.cleaned_data['description']
            entry.visibility = form.cleaned_data['visibility']
            entry.save()

            messages.success(request, 'Entry updated successfully!')
            # Go to entry view page after editiing
            return redirect('entries:view_entry', entry_id=entry.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # If GET request, pre-populate the form with current entry data
        # For images, leave 'content' blank so the text area is empty
        form = EntryForm(initial={
            'title': entry.title,
            'description': entry.description,
            'content_type': entry.content_type,
            'content': entry.content if entry.content_type.startswith('text') else '',
            'visibility': entry.visibility,
        })

    context = {'form': form, 'entry': entry}
    return render(request, 'entries/edit_entry.html', context)

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

    # Deleted entries hidden from non-staff
    if getattr(entry, "visibility", None) == "DELETED" and not request.user.is_staff:
        raise Http404("Entry not found")

    # Prefer model-level can_view if present
    can_view_method = getattr(entry, "can_view", None)
    if callable(can_view_method):
        if not entry.can_view(request.user):
            raise PermissionDenied
    else:
        # Fallback: PUBLIC/UNLISTED allowed; FRIENDS only author (until friends implemented)
        if entry.visibility == "FRIENDS":
            if not request.user.is_authenticated or request.user.id != entry.author.id:
                raise PermissionDenied
        # PUBLIC and UNLISTED visible to anyone
    context = {"entry": entry}
    return render(request, "entries/view_entry.html", context)

@login_required
def my_entries(request):
    """List all of the users entires"""
    entries = Entry.objects.filter(author=request.user).exclude(visibility='DELETED').order_by('-published')
    context = {'entries': entries}
    return render(request, 'entries/my_entries.html', context)