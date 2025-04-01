import sys
from io import BytesIO

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import MaxLengthValidator
from PIL import Image

from fedletic.models import FedleticUser


class LoginForm(forms.Form):
    username = forms.EmailField(
        max_length=64,
        required=True,
        label="email",
    )
    password = forms.CharField(
        required=True, min_length=8, max_length=64, widget=forms.PasswordInput()
    )


class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=64,
        required=True,
    )
    email = forms.EmailField(
        required=True,
    )
    password = forms.CharField(
        required=True, min_length=8, max_length=64, widget=forms.PasswordInput()
    )

    def clean_username(self):
        desired_username = self.cleaned_data["username"]
        if FedleticUser.objects.filter(username=desired_username).exists():
            raise ValidationError("Username already exists")

        return desired_username

    def clean_email(self):
        desired_email = self.cleaned_data["email"]
        if FedleticUser.objects.filter(email=desired_email).exists():
            raise ValidationError("Email already in use")
        return desired_email


class ProfileEditForm(forms.Form):
    AVATAR_MIN_SIZE = (128, 128)
    AVATAR_MAX_FILESIZE = 5
    HEADER_MIN_SIZE = (1200, 300)
    HEADER_MAX_FILESIZE = 10
    header_image = forms.ImageField(required=False)
    avatar = forms.ImageField(required=False)
    display_name = forms.CharField(max_length=150)
    summary = forms.CharField(
        max_length=500, required=False, validators=[MaxLengthValidator(500)]
    )

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar:
            return avatar

        # Check image dimensions for avatar
        width, height = get_image_dimensions(avatar)
        if width < self.AVATAR_MIN_SIZE[0] or height < self.AVATAR_MIN_SIZE[0]:
            raise forms.ValidationError(
                "Avatar image should be at least 400x400 pixels."
            )

        # Check file size (limit to 5MB)
        if avatar.size > self.AVATAR_MAX_FILESIZE * 1024 * 1024:
            raise forms.ValidationError("Avatar image file size must be under 5MB.")

        return avatar

    def clean_header_image(self):
        header = self.cleaned_data.get("header_image")
        if not header:
            return header

        # Check file size (limit to 10MB)
        if header.size > self.HEADER_MAX_FILESIZE * 1024 * 1024:
            raise forms.ValidationError("Header image file size must be under 10MB.")

        # Recommended minimum dimensions for header image
        width, height = get_image_dimensions(header)
        if self.HEADER_MIN_SIZE[0] < 1200 or self.HEADER_MIN_SIZE[1] < 300:
            raise forms.ValidationError(
                "Header image should be at least 1200x300 pixels for best results."
            )

        return header

    def clean_summary(self):
        summary = self.cleaned_data.get("summary")
        if summary and len(summary) > 500:
            raise forms.ValidationError("Bio must be 500 characters or less.")
        return summary

    def save(self, actor):
        """
        Update the actor model with form data

        Args:
            actor: The actor model instance to update

        Returns:
            The updated actor instance
        """
        if self.cleaned_data.get("display_name"):
            actor.name = self.cleaned_data["display_name"]

        if self.cleaned_data.get("summary"):
            actor.summary = self.cleaned_data["summary"]

        if self.cleaned_data.get("avatar"):
            # Process avatar image
            resized_avatar = self.handle_uploaded_image(
                self.cleaned_data["avatar"], "avatar"
            )
            # Delete old icon if it exists
            if actor.icon:
                actor.icon.delete(save=False)
            # Assign new image to the ImageField
            actor.icon = resized_avatar

        if self.cleaned_data.get("header_image"):
            # Process header image
            resized_header = self.handle_uploaded_image(
                self.cleaned_data["header_image"], "header"
            )
            # Delete old header if it exists
            if actor.header:
                actor.header.delete(save=False)
            # Assign new image to the ImageField
            actor.header = resized_header

        return actor

    def resize_image(self, image_file, max_width, max_height, is_avatar=False):
        """
        Resize an uploaded image while maintaining aspect ratio

        Args:
            image_file: The uploaded image file
            max_width: Maximum width for resized image
            max_height: Maximum height for resized image
            is_avatar: Boolean indicating if this is an avatar (square crop if True)

        Returns:
            InMemoryUploadedFile: The resized image file
        """
        img = Image.open(image_file)

        # Convert to RGB if necessary (removes transparency)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Get original dimensions
        width, height = img.size

        # Calculate new dimensions maintaining aspect ratio
        if is_avatar:
            # For avatar, we'll crop to a square first, then resize
            if width > height:
                # Landscape orientation
                left = (width - height) / 2
                top = 0
                right = (width + height) / 2
                bottom = height
            else:
                # Portrait orientation
                left = 0
                top = (height - width) / 2
                right = width
                bottom = (height + width) / 2

            # Crop to square
            img = img.crop((left, top, right, bottom))

            # Resize to target dimensions
            img = img.resize((max_width, max_height), Image.LANCZOS)
        else:
            # For header images, maintain aspect ratio
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)

        # Save the resized image to a BytesIO object
        output = BytesIO()
        img.save(output, format="JPEG", quality=85)
        output.seek(0)

        # Create a new InMemoryUploadedFile from the BytesIO object
        return InMemoryUploadedFile(
            output,
            "ImageField",
            f"{image_file.name.split('.')[0]}_resized.jpg",
            "image/jpeg",
            sys.getsizeof(output),
            None,
        )

    def handle_uploaded_image(self, image, image_type="avatar"):
        """
        Handle image upload including resizing

        Args:
            image: The uploaded image file
            image_type: Type of image ('avatar' or 'header')

        Returns:
            str: The URI for the saved image
        """
        # Set resize dimensions based on image type
        if image_type == "avatar":
            resized_image = self.resize_image(image, 400, 400, is_avatar=True)
        else:  # header
            resized_image = self.resize_image(image, 1500, 500, is_avatar=False)

        # Return the resized image file to be assigned to the model's ImageField
        # The model will handle storage when saved
        return resized_image
