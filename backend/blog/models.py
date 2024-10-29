from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.


# User = get_user_model()


class Tag(models.Model):
    name = models.CharField(max_length=25)

    def __str__(self):
        return self.name


class Blog(models.Model):
    title = models.CharField(max_length=100)
    picture = models.ImageField(upload_to='photos/blog/%Y/%m/%d', blank="True")
    created_at = models.DateTimeField()
    tags = models.ManyToManyField(Tag, related_name="tags")

    def __str__(self):
        return self.title


class BlogPart(models.Model):
    text = models.TextField()
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="blog_part")

    def __str__(self):
        return self.text[:10]
