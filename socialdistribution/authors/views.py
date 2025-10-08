from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Author
from entries.models import Entry
from .form import ProfileEditForm

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
    
    
    **currently a place holder, need to add entry logic**
    """
    author = request.user  
    
    entries = Entry.objects.filter(visibility='PUBLIC').exclude(visibility='DELETED')
    
    context = {
        'author': author,
        'entries': entries, 
    }
    
    return render(request, 'authors/stream.html', context)

