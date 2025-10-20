from django import forms
from .models import Entry, Visibility

class EntryForm(forms.Form):
    """Form for creating and editing entries"""
    
    title = forms.CharField(
        max_length=200,
        required=True,
        label='Title',
        widget=forms.TextInput(attrs={'placeholder': 'Entry title'})
    )
    
    description = forms.CharField(
        required=False,
        label='Description',
        widget=forms.Textarea(attrs={
            'placeholder': 'Brief description (optional)',
            'rows': 2
        })
    )
    
    content_type = forms.ChoiceField(
        choices=[('text/plain', 'Plain Text'),
                 ('image/png;base64', 'Image'),
                 # TODO: Add markdown in next iteration
        ],
        initial='text/plain',
        label='Content Type'
    )
    
    content = forms.CharField(
        required=False,
        label='Content',
        widget=forms.Textarea(attrs={
            'placeholder': 'Write your entry content here...',
            'rows': 10
        })
    )
    image = forms.ImageField(
        required=False,
        label='Upload Image',
        widget=forms.FileInput(attrs={
            'id': 'image-upload',
            'accept': 'image/png,image/jpeg,image/jpg'
        })
    )
    
    visibility = forms.ChoiceField(
        choices=[
            ('PUBLIC', 'Public'),
            ('FRIENDS', 'Friends Only'),
            ('UNLISTED', 'Unlisted'),
        ],
        initial='PUBLIC',
        label='Visibility'
    )

    def clean(self):
        cleaned_data = super().clean()
        # Only enforce required content if creating a new entry
        if self.initial.get('is_new', True):
            content_type = cleaned_data.get('content_type')
            content = cleaned_data.get('content')
            image = cleaned_data.get('image')

            existing_content = self.initial.get('content')

            if content_type.startswith('image'):
                if not image and not existing_content:
                    raise forms.ValidationError('Please upload an image for image entries.')
                cleaned_data['content'] = ''  # Clear text content if type is image
            else:
                if not content and not existing_content:
                    raise forms.ValidationError('Please provide content for text entries.')
                cleaned_data['image'] = None  # Clear image if type is text

        return cleaned_data