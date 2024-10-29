from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import LimitOffsetPagination

from .serializers import BlogSerializer, TagSerializer
from .models import Blog, Tag
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.filters import SearchFilter


class BlogApiView(ListAPIView, LimitOffsetPagination):
    default_limit = 10
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    serializer_class = BlogSerializer
    queryset = Blog.objects.prefetch_related("tags").prefetch_related("blog_part")
    filterset_fields = ["tags"]


class BlogReadApiView(RetrieveAPIView):
    serializer_class = BlogSerializer
    queryset = Blog.objects.prefetch_related("blog_part").prefetch_related("tags")


class TagApiView(ListAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class TagReadApiView(RetrieveAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
