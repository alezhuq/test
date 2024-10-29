from django.contrib import admin
from django.contrib.auth.models import Group

from .models import Tag, Blog, BlogPart

# Register your models here.

admin.site.register(Tag)
# admin.site.register(Blog)
# admin.site.register(BlogPart)
admin.site.unregister(Group)

class BlogPartInline(admin.TabularInline):
    model = BlogPart
    extra = 1


@admin.register(Blog)
class Blog(admin.ModelAdmin):
    inlines = [
        BlogPartInline
    ]
    search_fields = ("title",)
