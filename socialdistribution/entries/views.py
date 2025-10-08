from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Entry
from .forms import EntryForm
import uuid

@login_required
def create_entry(request):
    """Create a new entry"""
    if request.method == 'POST':
        form = EntryForm(request.POST)
        if form.is_valid():
            # Create the entry
            entry = Entry.objects.create(
                author=request.user,
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                content=form.cleaned_data['content'],
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
    """Edit an existing entry"""
    # Convert string ID to UUID
    try:
        entry_id_uuid = uuid.UUID(entry_id)
    except ValueError:
        messages.error(request, "Invalid entry ID.")
        return redirect('authors:stream')
    
    entry = get_object_or_404(Entry, id=entry_id_uuid)
    
    
    if request.user.id != entry.author.id:
        messages.error(request, "You can only edit your own entries.")
        return redirect('authors:stream')
    
    # Cannot edit deleted entries
    if entry.visibility == 'DELETED':
        messages.error(request, "Cannot edit deleted entries.")
        return redirect('authors:stream')
    
    if request.method == 'POST':
        form = EntryForm(request.POST)
        if form.is_valid():
            # Update the entry
            entry.title = form.cleaned_data['title']
            entry.description = form.cleaned_data['description']
            entry.content = form.cleaned_data['content']
            entry.content_type = form.cleaned_data['content_type']
            entry.visibility = form.cleaned_data['visibility']
            entry.save()
            
            messages.success(request, 'Entry updated successfully!')
            return redirect('entries:view_entry', entry_id=entry.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-populate form with current entry data
        form = EntryForm(initial={
            'title': entry.title,
            'description': entry.description,
            'content': entry.content,
            'content_type': entry.content_type,
            'visibility': entry.visibility,
        })
    
    context = {
        'form': form,
        'entry': entry
    }
    return render(request, 'entries/edit_entry.html', context)


@login_required
def delete_entry(request, entry_id):
    """Delete an entry (mark as DELETED)"""
    # Convert string ID to UUID
    try:
        entry_id_uuid = uuid.UUID(entry_id)
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


@login_required
def view_entry(request, entry_id):
    """View a single entry"""
    # Convert string ID to UUID
    try:
        entry_id_uuid = uuid.UUID(entry_id)
    except ValueError:
        messages.error(request, "Invalid entry ID.")
        return redirect('authors:stream')
    
    entry = get_object_or_404(Entry, id=entry_id_uuid)
    
    # Check if user has permission to view this entry
    if entry.visibility == 'DELETED':
        # Only admins can see deleted entries
        if not request.user.is_staff:
            messages.error(request, "This entry has been deleted.")
            return redirect('authors:stream')
    elif entry.visibility == 'FRIENDS':
        # TODO: Add a friends check when following/friends is implemented
        # For now, only author can see friends-only entries
        if request.user.id != entry.author.id:
            messages.error(request, "You don't have permission to view this entry.")
            return redirect('authors:stream')
    # PUBLIC and UNLISTED can be viewed by anyone (if they have the link)
    
    context = {'entry': entry}
    return render(request, 'entries/view_entry.html', context)

