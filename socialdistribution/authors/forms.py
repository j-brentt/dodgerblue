from django import forms
from .models import Author
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form that blocks unapproved users"""
    def confirm_login_allowed(self, user):
        if not user.is_approved:
            raise ValidationError("Your account is awaiting admin approval.", code='inactive')

class ProfileEditForm(forms.Form):
    """Form for editing author profile information"""
    
    display_name = forms.CharField(
        max_length=39,
        required=True,
        label='Display Name',
        widget=forms.TextInput(attrs={
            'placeholder': 'Your display name'
        })
    )
    
    github = forms.URLField(
        required=False,
        label='GitHub URL',
        widget=forms.URLInput(attrs={
            'placeholder': 'https://github.com/yourusername'
        })
    )
    
    profile_image = forms.URLField(
        required=False,
        label='Profile Image URL',
        widget=forms.URLInput(attrs={
            'placeholder': 'https://example.com/image.jpg'
        })
    )
    
    def clean_github(self):
        """Validate GitHub URL format"""
        github = self.cleaned_data.get('github')
        if github and not github.startswith('http'):
            raise forms.ValidationError('Please enter a valid URL starting with http:// or https://')
        return github
    
    def clean_profile_image(self):
        """Validate profile image URL format"""
        profile_image = self.cleaned_data.get('profile_image')
        if profile_image and not profile_image.startswith('http'):
            raise forms.ValidationError('Please enter a valid URL starting with http:// or https://')
        return profile_image
