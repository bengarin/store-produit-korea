from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    newPassword = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["currentPassword"]):
            raise serializers.ValidationError({"currentPassword": ["Mot de passe actuel incorrect."]})
        try:
            validate_password(attrs["newPassword"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"newPassword": list(exc.messages)}) from exc
        return attrs


def user_payload(user):
    """Format renvoyé au front (camelCase, comme le reste de l'API)."""
    role = user.role
    return {
        "id": user.pk,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "role": role.value if role else None,
        "roleLabel": role.label if role else None,
    }
