from rest_framework import serializers

from .models import Blog, BlogPart, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("name",)


class BlogPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPart
        fields = ("text",)


class BlogSerializer(serializers.ModelSerializer):
    blog_part = BlogPartSerializer(many=True)

    class Meta:
        model = Blog
        fields = ("title", "picture", "created_at", "blog_part")
