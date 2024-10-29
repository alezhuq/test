from django.contrib import admin
from django.forms import Textarea, TextInput
import rest_framework_simplejwt

from .models import User, Product, ProductInfo, ProductFlavor, FlavorImage, \
    ProductAdvantage, ProductFunction, ProductUse, FlavorLanguage, Address # ,ProductImage

from django.db import models


# Register your models here.


# admin.site.register(ProductInfo)
# admin.site.register(ProductSpec)
# admin.site.register(ProductFlavor)
# admin.site.register(ProductImage)
# admin.site.register(SpecImage)
# admin.site.register(ProductAdvantage)
# admin.site.register(ProductFunction)
# admin.site.register(ProductUse)
class AddressInline(admin.StackedInline):
    model = Address
    extra = 1


class CustomUserAdmin(admin.ModelAdmin):
    # Define fields, list_display, list_filter, etc., for the CustomUserAdmin as needed

    # Add the AddressInline to the User admin page
    inlines = [AddressInline]


# Register the CustomUserAdmin class with the User model
admin.site.register(User, CustomUserAdmin)


class FlavorLanguageInline(admin.TabularInline):
    model = FlavorLanguage
    extra = 1


class FlavorImageInline(admin.TabularInline):
    model = FlavorImage
    extra = 1


@admin.register(ProductFlavor)
class ProductFlavorAdmin(admin.ModelAdmin):
    inlines = [
        FlavorLanguageInline,
        FlavorImageInline
    ]
    search_fields = ("localized_name",)


class ProductAdvantageInline(admin.TabularInline):
    model = ProductAdvantage
    extra = 1


class ProductFunctionInline(admin.TabularInline):
    model = ProductFunction
    extra = 1


class ProductUseInline(admin.TabularInline):
    model = ProductUse
    extra = 1


class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '20'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 6, 'cols': 40})},
    }
    extra = 1


class ProductFlavorInline(admin.TabularInline):
    model = ProductFlavor
    extra = 1


# class ProductImageInline(admin.TabularInline):
#     model = ProductImage
#     extra = 1


@admin.register(Product)
class Product(admin.ModelAdmin):
    inlines = [
        ProductInfoInline,
        # ProductImageInline,
        ProductUseInline,
        ProductAdvantageInline,
        ProductFunctionInline
    ]
    search_fields = ("name",)
