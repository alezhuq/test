import json

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q, OuterRef, Subquery, Prefetch

from django.http import JsonResponse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.views import APIView

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .tasks import save_payment_method

from .models import User, ProductFunction, ProductAdvantage, ProductUse, FlavorLanguage, Address
from .serializers import CustomUserSerializer, LoginSerializer, FavoritesCreateSerializer, UserAddressSerializer, \
    AddCardSerializer, ProductNewSerializer
from django.conf import settings

import stripe

from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    RetrieveUpdateDestroyAPIView, GenericAPIView,
)
from blog.models import Blog
from .permissions import IsStaffOrReadOnly, IsStaff

from .models import ProductInfo, Product  # ,ProductImage
from .serializers import (
    ProductInfoSerializer,
    # ProductImageSerializer,
    # ProductCreateSerializer,
    ProductPreviewSerializer,
    ProductSerializer,
    FavoritesSerializer,
)
from .tasks import task1

"""-------------------------healthcheck-------------------------"""


def check(request):
    return JsonResponse({'status': 'working'})


class HelloView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        content = {'message': 'Hello, World!'}
        return Response(content)


"""-------------------------users-------------------------"""


class GoogleLogin(SocialLoginView):
    authentication_classes = []  # disable authentication
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:3000"
    client_class = OAuth2Client


class UserRegistrationView(GenericAPIView):
    """
    API endpoint that allows users to be registered and email confirmation to be sent.
    """
    serializer_class = CustomUserSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            current_site_info = get_current_site(request)
            mail_subject = 'The Activation link has been sent to your email address'
            user = serializer.data
            domain = current_site_info.domain
            uid = urlsafe_base64_encode(force_bytes(user.get('id')))
            user_obj = User.objects.get(id=user.get('id'))
            token = default_token_generator.make_token(user_obj)
            activation_link = f'http://{domain}/api/v1/shop/activate/{uid}/{token}'
            # make async task for email sending
            # task1.delay(mail_subject=mail_subject, activation_link=activation_link, user=user)

            return Response("Email was sent", status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserVerificationView(GenericAPIView):
    """
    API endpoint that handles user verification.
    """
    serializer_class = CustomUserSerializer

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_verified = True
            user.save()
            return Response("User successfully verified.", status=status.HTTP_200_OK)

        return Response("Invalid verification link.", status=status.HTTP_400_BAD_REQUEST)


class LoginView(CreateAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():

            data = serializer.validated_data
            response_data = {
                'refresh_token': data['refresh'],
                "access": data["access"],
            }
            response = Response(response_data, status=status.HTTP_200_OK)
            # response.set_cookie(key='refresh_token', value=data['refresh'], httponly=True,
            #                     secure=settings.SESSION_COOKIE_SECURE)
            # response.set_cookie(key='access_token', value=data['access'], httponly=True,
            #                     secure=settings.SESSION_COOKIE_SECURE)
            return response
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserFavoritesView(ListAPIView):
    serializer_class = FavoritesSerializer

    # permission_classes = (IsAuthenticated,)
    def get_queryset(self):
        user_id = self.request.user.id
        # if not userid == self.request.user:
        #     return Response("not authorized", status=status.HTTP_403_FORBIDDEN)

        queryset = User.objects.filter(id=user_id).prefetch_related(
            Prefetch(
                'favorites', queryset=Blog.objects.prefetch_related("blog_part").all()
            )
        ).all()
        return queryset


class UserCreateFavoritesView(CreateAPIView):
    serializer_class = FavoritesCreateSerializer

    # permission_classes = (IsAuthenticated,)
    def get_queryset(self):
        user_id = self.kwargs['pk']
        # if not userid == self.request.user:
        #     return Response("not authorized", status=status.HTTP_403_FORBIDDEN)

        queryset = User.objects.filter(id=user_id).prefetch_related(
            Prefetch(
                'favorites', queryset=Blog.objects.prefetch_related("blog_part").all()
            )
        ).all()
        return queryset


class UserUpdateDestroyFavoritesView(RetrieveUpdateDestroyAPIView):
    serializer_class = FavoritesCreateSerializer

    # permission_classes = (IsAuthenticated,)
    def get_queryset(self):
        user_id = self.request.user.id
        # if not userid == self.request.user:
        #     return Response("not authorized", status=status.HTTP_403_FORBIDDEN)

        queryset = User.objects.filter(id=user_id).prefetch_related(
            Prefetch(
                'favorites', queryset=Blog.objects.prefetch_related("blog_part").all()
            )
        ).all()
        return queryset


class UserAddressesView(ListAPIView):
    serializer_class = UserAddressSerializer

    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user_id = self.request.user.id
        # if not userid == self.request.user:
        #     return Response("not authorized", status=status.HTTP_403_FORBIDDEN)

        queryset = User.objects.filter(id=user_id).prefetch_related(
            Prefetch(
                'addresses', queryset=Address.objects.all()
            )
        ).all()
        return queryset


class UserCreateAddressesView(CreateAPIView):
    serializer_class = UserAddressSerializer
    permission_classes = (IsAuthenticated,)  # Ensure only authenticated users can create addresses

    def perform_create(self, serializer):
        # Save the address associated with the current authenticated user
        serializer.save(user=self.request.user)

    def get_queryset(self):
        # Ensure the queryset only contains the authenticated user's addresses
        return Address.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Perform the default create action
        response = super().create(request, *args, **kwargs)

        # Customize the response if needed (e.g., return user with addresses)
        return Response({
            "message": "Address created successfully",
            "address": response.data,
        }, status=status.HTTP_201_CREATED)


class UserGetUpdateDestroyAddressView(RetrieveUpdateDestroyAPIView):
    serializer_class = UserAddressSerializer

    # permission_classes = (IsAuthenticated,)
    def get_queryset(self):
        user_id = self.request.user.id
        # if not userid == self.request.user:
        #     return Response("not authorized", status=status.HTTP_403_FORBIDDEN)

        queryset = User.objects.filter(id=user_id).prefetch_related(
            Prefetch(
                'addresses', queryset=Address.objects.all()
            )
        ).all()
        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_payment_method(request):
    if request.method == 'POST':
        payment_method_id = request.data.get('payment_method_id')

        # Trigger the Celery task to save the payment method in the background
        save_payment_method.delay(request.user.id, payment_method_id)

        return Response({'message': 'Payment method is being saved in the background.'},
                        status=status.HTTP_202_ACCEPTED)


class AddCardView(CreateAPIView):
    serializer_class = AddCardSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Card added successfully"}, status=status.HTTP_200_OK)


"""-------------------------PRODUCTS public-------------------------"""

class ProductBasketApiView(ListAPIView):
    serializer_class = ProductNewSerializer
    permission_classes = (IsStaffOrReadOnly,)

    def get_queryset(self):
        language = self.request.query_params.get("lang", "en")
        queryset = Product.objects.prefetch_related(
            Prefetch(
                "product_info",
                queryset=ProductInfo.objects.exclude(~Q(language=language))
            )
        ).prefetch_related(
            "product_spec"
        ).filter(
            is_basket=True
        )
        return queryset

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Transform each product to the target structure
        transformed_data = []
        for product in queryset:
            transformed_product = {
                "id": product.id,
                "product_info": {
                    "localized_info_name": product.product_info.first().localized_info_name if product.product_info.exists() else "",
                    "description": product.product_info.first().description if product.product_info.exists() else "",
                },
                "preview_image": request.build_absolute_uri(product.preview_image.url),
                "product_spec": [
                    {
                        "name": "Test Flavour",  # Placeholder, adjust according to your actual data
                        "eu_quantity": product.product_spec.first().eu_quantity if product.product_spec.exists() else 0,
                        "ua_quantity": product.product_spec.first().ua_quantity if product.product_spec.exists() else 0,
                        "price_eu": product.product_spec.first().price_eur  if product.product_spec.exists() else 0,
                        "price_ua": product.product_spec.first().price_eur if product.product_spec.exists() else 0,
                    }
                ]
            }
            transformed_data.append(transformed_product)

        return Response(transformed_data)


class ProductNewApiView(ListAPIView):
    serializer_class = ProductNewSerializer
    permission_classes = (IsStaffOrReadOnly,)

    def get_queryset(self):
        language = self.request.query_params.get("lang", "en")
        queryset = Product.objects.prefetch_related(
            Prefetch(
                "product_info",
                queryset=ProductInfo.objects.exclude(~Q(language=language))
            )
        ).prefetch_related(
            "product_spec"
        ).filter(
            is_new=True
        )
        return queryset

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Transform each product to the target structure
        transformed_data = []
        for product in queryset:
            transformed_product = {
                "id": product.id,
                "product_info": {
                    "localized_info_name": product.product_info.first().localized_info_name if product.product_info.exists() else "",
                    "description": product.product_info.first().description if product.product_info.exists() else "",
                },
                "preview_image": request.build_absolute_uri(product.preview_image.url),
                "product_spec": [
                    {
                        "name": "Test Flavour",  # Placeholder, adjust according to your actual data
                        "eu_quantity": product.product_spec.first().eu_quantity if product.product_spec.exists() else 0,
                        "ua_quantity": product.product_spec.first().ua_quantity if product.product_spec.exists() else 0,
                        "price_eu": product.product_spec.first().price_eur  if product.product_spec.exists() else 0,
                        "price_ua": product.product_spec.first().price_eur if product.product_spec.exists() else 0,
                    }
                ]
            }
            transformed_data.append(transformed_product)

        return Response(transformed_data)

# cache

class ProductPreviewApiView(ListAPIView):
    serializer_class = ProductPreviewSerializer
    permission_classes = (IsStaffOrReadOnly,)

    def get_queryset(self):
        language = self.request.query_params.get("lang", "en")
        queryset = Product.objects.prefetch_related(
            Prefetch(
                "product_info",
                queryset=ProductInfo.objects.exclude(~Q(language=language))
            )
        ).prefetch_related(
            "product_spec"
        )
        return queryset

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Transform each product to the target structure
        transformed_data = []
        for product in queryset:
            transformed_product = {
                "id": product.id,
                "product_info": {
                    "localized_info_name": product.product_info.first().localized_info_name if product.product_info.exists() else "",
                    "description": product.product_info.first().description if product.product_info.exists() else "",
                },
                "preview_image": request.build_absolute_uri(product.preview_image.url),
                "product_spec": [
                    {
                        "name": "Test Flavour",  # Placeholder, adjust according to your actual data
                        "eu_quantity": product.product_spec.first().eu_quantity if product.product_spec.exists() else 0,
                        "ua_quantity": product.product_spec.first().ua_quantity if product.product_spec.exists() else 0,
                        "price_eu": product.product_spec.first().price_eur  if product.product_spec.exists() else 0,
                        "price_ua": product.product_spec.first().price_eur if product.product_spec.exists() else 0,
                    }
                ]
            }
            transformed_data.append(transformed_product)

        return Response(transformed_data)


class ProductRetrieveUpdateDestroyApiView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = (IsStaffOrReadOnly,)
    lookup_field = "id"

    def get_queryset(self):
        language = self.request.query_params.get("lang", "en")
        default_language = "en"

        # Primary query with requested language
        queryset = Product.objects.prefetch_related(
            Prefetch(
                "product_function",
                queryset=ProductFunction.objects.filter(language=language)
            ),
            Prefetch(
                "product_info",
                queryset=ProductInfo.objects.filter(language=language)
            ),
            Prefetch(
                "product_spec__product_flavor",
                queryset=FlavorLanguage.objects.filter(language=language)
            ),
            "product_spec__spec_image",
            Prefetch(
                "product_use",
                queryset=ProductUse.objects.filter(language=language)
            ),
            Prefetch(
                "product_advantage",
                queryset=ProductAdvantage.objects.filter(language=language)
            )
        )

        # Execute the initial query to check if all fields have results
        products = list(queryset)  # Force evaluation of the queryset

        # Check if any related fields are empty in the requested language
        missing_data = all(
            not getattr(product, "product_function").exists() or
            not getattr(product, "product_info").exists() or
            not all(spec.product_flavor.exists() for spec in product.product_spec.all()) or
            not getattr(product, "product_use").exists() or
            not getattr(product, "product_advantage").exists()
            for product in products
        )

        # If any related data is missing, fall back to default language
        if missing_data:
            queryset = Product.objects.prefetch_related(
                Prefetch(
                    "product_function",
                    queryset=ProductFunction.objects.filter(language=default_language)
                ),
                Prefetch(
                    "product_info",
                    queryset=ProductInfo.objects.filter(language=default_language)
                ),
                Prefetch(
                    "product_spec__product_flavor",
                    queryset=FlavorLanguage.objects.filter(language=default_language)
                ),
                "product_spec__spec_image",
                Prefetch(
                    "product_use",
                    queryset=ProductUse.objects.filter(language=default_language)
                ),
                Prefetch(
                    "product_advantage",
                    queryset=ProductAdvantage.objects.filter(language=default_language)
                )
            )
        for elem in queryset:
            for i in elem.product_spec.all():
                print(vars(i))
        return queryset

    def get(self, request, *args, **kwargs):
        product = self.get_object()
        # Get the single product based on lookup field
        product_info = product.product_info.first() if product.product_info.exists() else None
        product_function = product.product_function.first().info if product.product_function.exists() else None
        product_advantage = product.product_advantage.first().info if product.product_advantage.exists() else None
        product_use = product.product_use.first().info if product.product_use.exists() else None
        # product_language = product.product_info.first() if product.product_info.exists()

        for spec in product.product_spec.all():
            print(vars(spec))

        # Transform product_spec data
        product_spec_list = []
        for spec in product.product_spec.all():
            product_flavor = spec.product_flavor.first() if spec.product_flavor.exists() else None
            spec_images = [{"img_name": img.name, "image": request.build_absolute_uri(img.image.url)} for img in
                           spec.spec_image.all()]

            transformed_spec = {
                "id": spec.id,
                "eu_quantity": spec.eu_quantity,
                "ua_quantity": spec.ua_quantity,
                "localized_name": product_flavor.localized_flavor_name,
                "spec_image": spec_images,
                "price_usd": spec.price_usd,  # Adjust as necessary
                "price_uah": spec.price_uah,  # Adjust as necessary
                "price_eur": spec.price_eur  # Adjust as necessary
            }
            product_spec_list.append(transformed_spec)

        transformed_data = {
            "id": product.id,
            "product_spec": product_spec_list,
            "product_info": {
                "localized_info_name": product_info.localized_info_name,
                "description": product_info.description,
            },
            "product_function": product_function,
            "product_advantage": product_advantage,
            "product_use": product_use
        }

        return Response(transformed_data)


"""-------------------------PRODUCTS private-------------------------"""


# class ProductCreateApiView(CreateAPIView):
#     serializer_class = ProductCreateSerializer
#     permission_classes = (IsStaffOrReadOnly,)


class ProductInfoCreateApiView(CreateAPIView):
    serializer_class = ProductInfoSerializer
    permission_classes = (IsStaff,)


class ProductInfoRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProductInfoSerializer
    permission_classes = (IsStaff,)

    def get_queryset(self):
        product_id = self.kwargs['id']
        pk = self.kwargs['pk']
        queryset = ProductInfo.objects.select_related("product").get(product_id=product_id, id=pk)
        return queryset

# class ProductImageCreateApiView(CreateAPIView):
#     serializer_class = ProductImageSerializer
#     permission_classes = (IsStaff,)
#
#     def get_queryset(self):
#         pass
#
#
# class ProductImageRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
#     serializer_class = ProductImageSerializer
#     permission_classes = (IsStaff,)
#
#     def get_queryset(self):
#         product_id = self.kwargs['id']
#         image_id = self.kwargs['image_id']
#         queryset = ProductImage.objects.select_related(Product).get(product_id=product_id, id=image_id)
#         return queryset
