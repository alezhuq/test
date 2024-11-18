from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    check,
    HelloView,
    UserRegistrationView,
    UserFavoritesView,
    LoginView,
    ProductPreviewApiView,
    ProductRetrieveUpdateDestroyApiView,
    # ProductCreateApiView,
    ProductInfoCreateApiView,
    ProductInfoRetrieveUpdateDestroyAPIView,
    # ProductImageCreateApiView,
    # ProductImageRetrieveUpdateDestroyAPIView,
    UserVerificationView,
    GoogleLogin, add_payment_method, UserCreateFavoritesView, UserAddressesView, UserCreateAddressesView,
    UserUpdateDestroyFavoritesView, UserGetUpdateDestroyAddressView, AddCardView, ProductNewApiView,
    ProductBasketApiView,

)


urlpatterns = [
    path('', check),

    # user
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('hello/', HelloView.as_view(), name='hello'),
    path('register/', UserRegistrationView.as_view(), name='user_registration'),
    path('google/', GoogleLogin.as_view()),
    path('activate/<str:uidb64>/<str:token>/', UserVerificationView.as_view(), name='activate_email'),
    path('favorites/', UserFavoritesView.as_view(), name='user_favorites'),
    path('favorites/<int:pk>', UserUpdateDestroyFavoritesView.as_view(), name='user_favorites'),
    path('favorites/add/', UserCreateFavoritesView.as_view(), name='user_favorites_add'),
    path('address/', UserAddressesView.as_view(), name='user_addresses'),
    path('address/<int:pk>', UserGetUpdateDestroyAddressView.as_view(), name='user_addresses'),
    path('address/add/', UserCreateAddressesView.as_view(), name='user_addresses_add'),
    path("user/payment/add/", AddCardView.as_view(), name="user_payment_add"),
    path('add_payment_method/', add_payment_method, name='add_payment_method'),
    # product
    # *public*
    path('product/', ProductPreviewApiView.as_view()),
    path('product/new/', ProductNewApiView.as_view()),
    path('product/basket/', ProductBasketApiView.as_view()),
    path('product/<int:id>/', ProductRetrieveUpdateDestroyApiView.as_view()),


    # *private*
    # path('product/create/', ProductCreateApiView.as_view()),




    # path('product/<int:id>/info', ProductInfoCreateApiView.as_view()),
    # path('product/<int:id>/info/<int:pk>', ProductInfoRetrieveUpdateDestroyAPIView.as_view()),


]
