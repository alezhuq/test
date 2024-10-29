from django.urls import path
from .views import (
    TagApiView,
    TagReadApiView,
    BlogApiView,
    BlogReadApiView,
)

urlpatterns = [
    path('', BlogApiView.as_view()),
    path('<int:pk>', BlogReadApiView.as_view()),

    path('tag/', TagApiView.as_view()),
    path('tag/<int:pk>', TagReadApiView.as_view()),
]
