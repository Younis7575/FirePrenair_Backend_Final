# forms.py
from django import forms
from .models import *
from profiles.models import CustomUser
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import password_validation


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Review Title", "class": ""}
            ),
            "body": forms.Textarea(
                attrs={
                    "placeholder": "Your comment",
                    "class": "comment-form",
                    "cols": 30,
                    "rows": 10,
                }
            ),
            "rating": forms.Select(choices=[(i, f"{i} Star") for i in range(1, 6)]),
        }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "username",
            "name",
            # "email",
            "phone_no",
            "digi_description",
            "country",
            "profile_pic",
            "digi_cover_photo",
            "digi_speciality",
            "digi_portfolio",
            "digi_speciality",
            
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Old password"}),
        label="Old Password",
        strip=False,
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "New password"}),
        label="New Password",
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm new password"}),
        label="Confirm New Password",
        strip=False,
    )

    class Meta:
        fields = ["old_password", "new_password1", "new_password2"]


class ProductUploadForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "title",
            "description",
            "price",
            "category",
            "image",
            "files_included",
            "downloadable_file",
            "softwares",
            "size",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "files_included": forms.TextInput(
                attrs={"placeholder": "e.g., .zip, .pdf"}
            ),
            "softwares": forms.TextInput(
                attrs={"placeholder": "e.g., Photoshop, Illustrator"}
            ),
            "downloadable_file": forms.ClearableFileInput(
                attrs={"style": "display: none;", "id": "id_downloadable_file"}
            ),
            "image": forms.ClearableFileInput(
                attrs={"style": "display: none;", "id": "id_image"}
            ),
        }

        # Override the label for the image field

    def __init__(self, *args, **kwargs):
        super(ProductUploadForm, self).__init__(*args, **kwargs)
        self.fields["image"].label = "Preview Image"
