# blog/forms.py
from django import forms
from .models import Post, Comment, UserPreference
import bleach
from taggit.forms import TagField

class PostForm(forms.ModelForm):
    def clean_content(self):
        content = self.cleaned_data["content"]
        return bleach.clean(
            content,
            tags=["p", "b", "i", "a", "img"],
            attributes={"a": ["href"], "img": ["src"]},
        )

    class Meta:
        model = Post
        fields = ["title", "content", "picture", "category", "tags"]
        widgets = {
            "tags": forms.TextInput(attrs={"data-role": "tagsinput"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].widget = forms.Textarea(attrs={"id": "editor"})

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }

class UserPreferenceForm(forms.ModelForm):
    preferred_tags = TagField(required=False, help_text="Enter tags you like (e.g., python, travel).")

    class Meta:
        model = UserPreference
        fields = ['preferred_tags']