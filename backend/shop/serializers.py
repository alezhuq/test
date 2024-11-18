from datetime import date

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
import stripe
from .models import (
    User,
    ProductInfo,
    # ProductImage,
    Product,

    ProductAdvantage,
    ProductFunction,
    ProductUse,
    ProductFlavor, FlavorImage, FlavorLanguage, Address,
)

from blog.serializers import BlogSerializer
from allauth.account.models import EmailConfirmation, EmailAddress


def validate_birthdate(value):
    if value.date() > date.today():
        raise ValidationError("Birthdate can't be in the future.")
    return value


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise ValidationError("Invalid email address")
        return value

    def validate_birthdate(self, value):
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))

        if age < 18:
            raise serializers.ValidationError("You must be at least 18 years old to register.")

        return value

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'birthdate')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):

        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            birthdate=validated_data['birthdate'],
            password=validated_data['password'],
            is_verified=False,
            is_staff=False
        )

        try:
            stripe_customer = stripe.Customer.create(
                email=validated_data['email'],
                name=f"{validated_data['first_name']} {validated_data['last_name']}"
            )
            # Optionally, store the Stripe customer ID in your user model
            user.stripe_customer_id = stripe_customer['id']
            user.save()
        except stripe.error.StripeError as e:
            # Handle Stripe error (logging, notifications, etc.)
            raise serializers.ValidationError(f"Stripe error: {str(e)}")

        # stripe customer create

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.pop('email')
        password = data.pop('password')
        if not email or not password:
            raise serializers.ValidationError('Please provide both email and password.')
        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        refresh = RefreshToken.for_user(user)
        print(f"{refresh=}")
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        return data

    def get_token_backend(self):
        return settings.SIMPLE_JWT['AUTH_TOKEN_CLASSES'][0]

    def encode_jwt(self, payload):
        token_backend = self.get_token_backend()
        key = token_backend.get_private_key()
        return token_backend.encode(payload, key)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        refresh_token = representation['refresh']
        access_token = representation['access']
        payload = {'refresh': refresh_token, 'access': access_token}
        representation['jwt'] = self.encode_jwt(payload)
        return representation


class FavoritesSerializer(serializers.ModelSerializer):
    favorites = BlogSerializer(many=True)

    class Meta:
        model = User
        fields = ("id", "favorites")


class FavoritesCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "favorites")


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("country", "first_name", "last_name", "city", "address", "zip_code", "apartment", "phonenum",)

    def to_stripe_address(self):
        """Method to convert the Address instance to Stripe-compatible address dict."""
        return {
            "line1": self.validated_data.get("address"),
            "line2": self.validated_data.get("apartment", ""),
            "city": self.validated_data.get("city"),
            "postal_code": self.validated_data.get("zip_code"),
            "country": self.validated_data.get("country").code  # Assumes CountryField stores country codes
        }

    def create_stripe_customer(self, user):
        """Create a Stripe customer with address information"""
        try:
            stripe_customer = stripe.Customer.create(
                email=user.email,
                name=f"{self.validated_data.get('first_name')} {self.validated_data.get('last_name')}",
                address=self.to_stripe_address(),
                phone=self.validated_data.get('phonenum')
            )
            return stripe_customer
        except stripe.error.StripeError as e:
            raise serializers.ValidationError(f"Stripe error: {str(e)}")


class AddCardSerializer(serializers.Serializer):
    payment_method_id = serializers.CharField()

    def save(self, **kwargs):
        request = self.context.get("request")
        user = request.user

        # Create or retrieve Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}"
            )
            user.stripe_customer_id = customer['id']
            user.save()

        try:
            # Attach the payment method to the Stripe customer
            stripe.PaymentMethod.attach(
                self.validated_data['payment_method_id'],
                customer=user.stripe_customer_id,
            )

            # Set the payment method as the default payment method for invoices
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={
                    'default_payment_method': self.validated_data['payment_method_id'],
                },
            )
        except stripe.error.StripeError as e:
            raise serializers.ValidationError(f"Stripe error: {str(e)}")

        return {"message": "Card added successfully"}


class UserAddressSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True)

    class Meta:
        model = User
        fields = ("id", "addresses",)

    def create(self, validated_data):
        addresses = validated_data.pop("addresses")
        user = self.context['request'].user
        for address in addresses:
            Address.objects.create(user=user, **address)

        return user


class ProductAdvantageSerializer(serializers.ModelSerializer):
    # Directly returning 'info' field instead of nested structure
    info = serializers.CharField()

    class Meta:
        model = ProductAdvantage
        fields = ["info"]


class ProductFunctionSerializer(serializers.ModelSerializer):
    # Directly returning 'info' field instead of nested structure
    info = serializers.CharField()

    class Meta:
        model = ProductFunction
        fields = ["info"]


class ProductUseSerializer(serializers.ModelSerializer):
    # Directly returning 'info' field instead of nested structure
    info = serializers.CharField()

    class Meta:
        model = ProductUse
        fields = ["info"]


class SpecImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlavorImage
        fields = ("name", "image",)


class ProductFlavorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlavorLanguage
        fields = ("localized_flavor_name",)


class ProductPreviewSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFlavor
        fields = ("name", "eu_quantity", "ua_quantity")


class ProductSpecSerializer(serializers.ModelSerializer):
    product_flavor = ProductFlavorSerializer(many=True)
    spec_image = SpecImageSerializer(many=True)

    class Meta:
        model = ProductFlavor
        fields = (
            "id", "name", "eu_quantity", "ua_quantity", "product_flavor", "spec_image", "price_usd", "price_uah",
            "price_eur",)


class ProductInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductInfo
        fields = ["localized_info_name", "description", "language"]
        lookup_field = "info_id"


# class ProductImageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProductImage
#         fields = ["name", "image"]


class ProductNewSerializer(serializers.ModelSerializer):
    # Set many=False for product_info, product_function, product_advantage, and product_use

    product_info = ProductInfoSerializer(many=True)
    product_spec = ProductPreviewSpecSerializer(many=True)

    class Meta:
        model = Product
        fields = ("id", "preview_image", "image_alt" "product_info", "product_spec")


class ProductBasketerializer(serializers.ModelSerializer):
    # Set many=False for product_info, product_function, product_advantage, and product_use

    product_info = ProductInfoSerializer(many=True)
    product_spec = ProductPreviewSpecSerializer(many=True)

    class Meta:
        model = Product
        fields = ("id", "preview_image", "image_alt" "product_info", "product_spec")


class ProductPreviewSerializer(serializers.ModelSerializer):
    # Set many=False for product_info, product_function, product_advantage, and product_use

    product_info = ProductInfoSerializer(many=True)
    product_spec = ProductPreviewSpecSerializer(many=True)
    product_function = ProductFunctionSerializer(many=True)
    product_advantage = ProductAdvantageSerializer(many=True)
    product_use = ProductUseSerializer(many=True)

    class Meta:
        model = Product
        fields = (
            "id", "preview_image", "image_alt", "product_info", "product_spec", "product_function", "product_advantage",
            "product_use")


class ProductSerializer(serializers.ModelSerializer):
    product_spec = ProductSpecSerializer(many=True)
    product_info = ProductInfoSerializer(many=True)
    product_function = ProductFunctionSerializer(many=True)
    product_advantage = ProductAdvantageSerializer(many=True)
    product_use = ProductUseSerializer(many=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "product_spec",
            "product_info",
            "product_function",
            "product_advantage",
            "product_use",
        )

# class ProductCreateSerializer(serializers.ModelSerializer):
#     product_quantity = ProductQuantitySerializer(many=True, required=False)
#     product_image = ProductImageSerializer(many=True, required=False)
#     product_info = ProductInfoSerializer(many=True, required=False)
#
#     class Meta:
#         model = Product
#         fields = ["preview_image", "weight", "product_quantity", "product_info", "product_image"]
#
#     def create(self, validated_data):
#         product_info_data = validated_data.pop("product_info")
#         product_quantity_data = validated_data.pop("product_quantity")
#         product_image_data = validated_data.pop("product_image")
#
#         product = Product.objects.create(**validated_data)
#
#         for info in product_info_data:
#             ProductInfo.objects.create(product=product, **info)
#
#         for quantity in product_quantity_data:
#             ProductQuantity.objects.create(product=product, **quantity)
#
#         for image in product_image_data:
#             ProductImage.objects.create(product=product, **image)
#
#         return product
