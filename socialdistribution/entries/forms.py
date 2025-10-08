from django import forms
from .models import Entry

class EntryForm(forms.Form):
    """Form for creating and editing entries"""
    
    title = forms.CharField(
        max_length=200,
        required=True,
        label='Title',
        widget=forms.TextInput(attrs={
            'placeholder': 'Entry title'
        })
    )
    
    description = forms.CharField(
        required=False,
        label='Description',
        widget=forms.Textarea(attrs={
            'placeholder': 'Brief description (optional)',
            'rows': 2
        })
    )
    
    content = forms.CharField(
        required=True,
        label='Content',
        widget=forms.Textarea(attrs={
            'placeholder': 'Write your entry content here...',
            'rows': 10
        })
    )
    
    content_type = forms.ChoiceField(
        choices=Entry.CONTENT_TYPE_CHOICES,
        initial='text/plain',
        label='Content Type'
    )
    
    visibility = forms.ChoiceField(
        choices=Entry.VISIBILITY_CHOICES,
        initial='PUBLIC',
        label='Visibility'
    )