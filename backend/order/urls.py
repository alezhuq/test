from django.urls import path

from .views import (

    SubscriptionAPIView,
    OrderCreateView, temp, my_webhook_view, create_tnn_np,
    SubscriptionCreateView, OrderAPIView, OrderListAPIView
)


urlpatterns = [
    # order
    path('', OrderListAPIView.as_view()),
    path('<int:pk>/', OrderAPIView.as_view()),

    path('create/', OrderCreateView.as_view()),
    path('subscribe/', SubscriptionCreateView.as_view()),
    path("sub/success/", temp),
    path("sub/cancel/", temp),
    path("payment/success/", temp),
    path("payment/cancel/", temp),
    path("payment/webhook/", my_webhook_view),
    path("test/", create_tnn_np),
]
