# forms.py
from django import forms
from digi_prenair.models import *
from edu_prenair.models import *
from profiles.models import CustomUser
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import password_validation
from .models import *


# class ProfileUpdateForm(forms.ModelForm):
#     class Meta:
#         model = CustomUser
#         fields = [
#             "name",
#             "username",
#             "phone_no",
#             "bio",
#             "profile_pic",
#             "age",
#             "twitter",
#             "facebook",
#             "linkedin",
#             "instagram",
#             "youtube",
#             "pinterest",
#         ]
#         widgets = {
#             "name": forms.TextInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg capitalize",
#                     "placeholder": "Full Name...",
#                     "required": True,
#                 }
#             ),
#             "username": forms.TextInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg ",
#                     "placeholder": "Username...",
#                 }
#             ),
#             "phone_no": forms.TextInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "Phone Number...",
#                     "required": True,
#                 }
#             ),
#             "bio": forms.Textarea(
#                 attrs={
#                     "class": "w-full px-4 py-3 mt-2 border-line rounded-lg",
#                     "rows": 8,
#                     "placeholder": "Write a short bio...",
#                 }
#             ),
#             "profile_pic": forms.FileInput(
#                 attrs={
#                     "class": "py-1 px-3 rounded bg-line upload_file cursor-pointer",
#                     "label": "Upload Profile Picture",
#                     "accept": "image/*",
#                 }
#             ),
#             "age": forms.NumberInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "Age...",
#                     "required": True,
#                 }
#             ),
#             "twitter": forms.URLInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "Twitter URL...",
#                 }
#             ),
#             "facebook": forms.URLInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "Facebook URL...",
#                 }
#             ),
#             "linkedin": forms.URLInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "LinkedIn URL...",
#                 }
#             ),
#             "instagram": forms.URLInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "Instagram URL...",
#                 }
#             ),
#             "youtube": forms.URLInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "YouTube URL...",
#                 }
#             ),
#             "pinterest": forms.URLInput(
#                 attrs={
#                     "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
#                     "placeholder": "Pinterest URL...",
#                 }
#             ),
#         }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "name",
            "username",
            "phone_no",
            "bio",
            "profile_pic",
            "date_of_birth",
            "country",
            "city",
            "province",
            "postal_code",
            "customer_type",
            "company_name",
            "company_number",
            "identity_type",
            "identity_number",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg capitalize",
                    "placeholder": "Full Name...",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Username...",
                }
            ),
            "phone_no": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Phone Number...",
                }
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-3 mt-2 border-line rounded-lg",
                    "rows": 8,
                    "placeholder": "Write a short bio...",
                }
            ),
            "profile_pic": forms.FileInput(
                attrs={
                    "class": "py-1 px-3 rounded bg-line upload_file cursor-pointer",
                    "accept": "image/*",
                }
            ),
            "date_of_birth": forms.DateInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Date of Birth...",
                    "type": "date"
                }
            ),

            "country": forms.HiddenInput(),  # Hidden field, will be handled by custom select
            "city": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "City...",
                }
            ),
            "province": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Province / State...",
                }
            ),
            "postal_code": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Postal Code...",
                }
            ),
            "identity_type": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg",
                    "placeholder": "Identity Type...",
                }
            ),
            "identity_number": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Identity Number...",
                }
            ),
            "customer_type": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg",
                    "placeholder": "Customer Type...",
                }
            ),
            "company_name": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Company Name...",
                }
            ),
            "company_number": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Company Number...",
                }
            ),
            "tax_number": forms.TextInput(
                attrs={
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Tax Number...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        is_username_changed = kwargs.pop("is_username_changed", False)
        super().__init__(*args, **kwargs)
        if is_username_changed:
            self.fields["username"].widget.attrs["readonly"] = True


# class ProductUploadForm(forms.ModelForm):
#     class Meta:
#         model = Product
#         fields = [
#             "title",
#             "description",
#             "price",
#             "category",
#             "category_l_2",
#             "category_l_3",
#             "image",
#             "files_included",
#             "downloadable_file",
#             "softwares",
#             "size",
#         ]
#         widgets = {
#             "title": forms.TextInput(attrs={"placeholder": "Title..."}),
#             "description": forms.Textarea(attrs={"class": "form_editor"}),
#             "price": forms.NumberInput(attrs={"placeholder": "Price..."}),
#             "files_included": forms.TextInput(
#                 attrs={"placeholder": ".png, .pdf, .zip..."}
#             ),
#             "softwares": forms.TextInput(
#                 attrs={"placeholder": "Adobe PS, Ms Word, Canva..."}
#             ),
#             "size": forms.TextInput(attrs={"placeholder": "200MB..."}),
#             "image": forms.ClearableFileInput(
#                 attrs={"class": "uploadImage", "accept": "image/*"}
#             ),
#             "downloadable_file": forms.ClearableFileInput(
#                 attrs={"class": "uploadFile", "accept": "application/*"}
#             ),
#         }


class ProductUploadForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "title",
            "description",
            "price",
            "category",
            "category_l_2",
            "category_l_3",
            "image",
            "files_included",
            "downloadable_file",
            "softwares",
            "size",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Title...",
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                }
            ),
            "description": forms.Textarea(
                attrs={"class": "w-full h-40 px-4 mt-2 border-line rounded-lg"}
            ),
            "price": forms.NumberInput(
                attrs={
                    "placeholder": "Price...",
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                }
            ),
            "files_included": forms.TextInput(
                attrs={
                    "placeholder": ".png, .pdf, .zip...",
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                }
            ),
            "category_l_2": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg",
                    "id": "category_l_2",  # Add IDs for easier targeting in JS
                }
            ),
            "category_l_3": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg",
                    "id": "category_l_3",  # Add IDs for easier targeting in JS
                }
            ),
            "softwares": forms.TextInput(
                attrs={
                    "placeholder": "Adobe PS, Ms Word, Canva...",
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                }
            ),
            "size": forms.TextInput(
                attrs={
                    "placeholder": "200MB...",
                    "class": "w-full h-12 px-4 mt-2 border-line rounded-lg",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "uploadImage", "accept": "image/*"}
            ),
            "downloadable_file": forms.ClearableFileInput(
                attrs={"class": "uploadFile", "accept": "application/*"}
            ),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "category_l_1",
            "category_l_2",
            "category_l_3",
            "description",
            "requirements",
            "language",
            "price",
            "thumbnail",
            "duration",
            "level",
            "is_free",
            "discount_price",
            "monthly_subscription",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Enter course title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control w-full h-40 px-4 mt-2 border-line rounded-lg",
                    "rows": 5,
                    "placeholder": "Enter course description",
                }
            ),
            "requirements": forms.TextInput(
                attrs={
                    "class": "form-control w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Enter course requirements",
                }
            ),
            "language": forms.TextInput(
                attrs={
                    "class": "form-control w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Enter language",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Enter price",
                }
            ),
            "thumbnail": forms.FileInput(
                attrs={"class": "form-control w-full px-4 mt-2 border-line rounded-lg"}
            ),
            "duration": forms.NumberInput(
                attrs={
                    "class": "form-control w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Enter duration in hours",
                }
            ),
            "category_l_1": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg",
                    "id": "category_l_1",  # Add IDs for easier targeting in JS
                }
            ),
            "category_l_2": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg",
                    "id": "category_l_2",  # Add IDs for easier targeting in JS
                }
            ),
            "category_l_3": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg",
                    "id": "category_l_3",  # Add IDs for easier targeting in JS
                }
            ),
            "level": forms.Select(
                attrs={
                    "class": "form-control select_block flex items-center w-full h-12 pr-10 pl-4 mt-2 border border-line rounded-lg"
                }
            ),
            "is_free": forms.CheckboxInput(
                attrs={
                    "class": "form-control form-checkbox h-5 w-5 text-blue-600",
                }
            ),
            "discount_price": forms.NumberInput(
                attrs={
                    "class": "form-control w-full h-12 px-4 mt-2 border-line rounded-lg",
                    "placeholder": "Enter discount price",
                }
            ),
            "monthly_subscription": forms.CheckboxInput(
                attrs={
                    "class": "form-control form-checkbox h-5 w-5 text-blue-600",
                }
            ),
        }
        labels = {
            "title": "Course Title",
            "description": "Course Description",
            "title": "Course Title",
            "description": "Course Description",
            "requirements": "Requirements",
            "language": "Language",
            "price": "Price",
            "thumbnail": "Thumbnail Image",
            "duration": "Duration (hours)",
            "category_l_1": "Level 1 Category",
            "category_l_2": "Level 2 Category",
            "category_l_3": "Level 3 Category",
            "level": "Course Level",
            "is_free": "Free Course",
            "discount_price": "Discount Price",
            "monthly_subscription": "Monthly Subscription",
        }

    def clean(self):
        cleaned_data = super().clean()
        is_free = cleaned_data.get("is_free")
        discount_price = cleaned_data.get("discount_price")

        if is_free and discount_price:
            raise forms.ValidationError("A free course cannot have a discount price.")

        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Old Password",
                "class": "w-1/2 h-12 px-4 mt-2 border-line rounded-lg",
                "id": "oldPass",
            }
        ),
        label="Old Password",
        strip=False,
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "New Password",
                "class": "w-1/2 h-12 px-4 mt-2 border-line rounded-lg",
                "id": "newPass",
            }
        ),
        label="New Password",
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm New Password",
                "class": "w-1/2 h-12 px-4 mt-2 border-line rounded-lg",
                "id": "confirmPass",
            }
        ),
        label="Confirm New Password",
        strip=False,
    )

    class Meta:
        fields = ["old_password", "new_password1", "new_password2"]


# class PayoneerAccountForm(forms.ModelForm):
#     class Meta:
#         model = PayoneerAccount
#         fields = ['payee_id']
