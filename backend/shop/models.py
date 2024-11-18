from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import UserManager
from blog.models import Blog
from django_countries.fields import CountryField


# Create your models here.

class User(AbstractUser):
    username = None

    REQUIRED_FIELDS = []
    email = models.EmailField(max_length=50, unique=True)
    USERNAME_FIELD = 'email'
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    # later change default to false right here \|/
    is_verified = models.BooleanField(default=True, help_text="checks if user has verified their email")
    last_active = models.DateTimeField(blank=True, null=True)  # some date (core logic - last purchase)
    birthdate = models.DateField(null=True, help_text="Date of  user birth")
    phonenum = models.CharField(max_length=13)  # +234567890123  phone (+11 011 111 11 11)
    favorites = models.ManyToManyField(Blog, related_name="favorites")  # users add posts to favorites
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    objects = UserManager()

    # payments (separate db table) maybe yesss????
    # addresses probably yess
    def __str__(self):
        return self.email


class PaymentMethod(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_method_id = models.CharField(max_length=50, unique=True)
    card_brand = models.CharField(max_length=20)
    last4 = models.CharField(max_length=4)

    def __str__(self):
        return f'{self.user.username} - {self.card_brand} ending in {self.last4}'


# address book :
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    country = CountryField()
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    city = models.CharField(max_length=30)
    address = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    apartment = models.CharField(max_length=10)
    phonenum = models.CharField(max_length=13)


class Language(models.TextChoices):
    UA = "ua", "Ukrainian"
    CZ = "cz", "Czech"
    EN = "en", "English"
    RU = "ru", "Russian"
    IT = "it", "Italian"
    FR = "fr", "French"
    ES = "es", "Espanol"
    DE = "de", "Deutch"


# change of code

"""-------------------------PRODUCTS-------------------------"""


class Product(models.Model):
    name = models.CharField(max_length=20, unique=True)
    weight = models.IntegerField(help_text="weight of product in grams")
    preview_image = models.ImageField(upload_to='photos/shop/%Y/%m/%d', blank="True")
    image_alt = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True, help_text="instead of deleting products, you can deactivate them")
    is_new = models.BooleanField(default=False, help_text="mark products for new suggestion")
    is_basket = models.BooleanField(default=False, help_text="mark products for basket suggestion")
    length = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()

    def __str__(self):
        return self.name


# class ProductImage(models.Model):
#     name = models.CharField(max_length=20, unique=True)
#     image = models.ImageField(upload_to='photos/shop/%Y/%m/%d', blank="True")
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_image")
#
#     def __str__(self):
#         return f'{self.product.name} : {self.name}'


class ProductFlavor(models.Model):
    name = models.CharField(max_length=20)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_spec")
    is_active = models.BooleanField(default=True, help_text="instead of deleting specs, you can deactivate them")
    stripe_price_eu_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_price_us_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_price_ua_id = models.CharField(max_length=255, null=True, blank=True)
    eu_quantity = models.PositiveIntegerField()
    us_quantity = models.PositiveIntegerField()
    ua_quantity = models.PositiveIntegerField()
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    price_uah = models.DecimalField(max_digits=10, decimal_places=2)
    price_eur = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product.name} {self.name}'


class FlavorLanguage(models.Model):
    localized_flavor_name = models.CharField(max_length=20)
    language = models.CharField(max_length=20, choices=Language.choices)
    spec = models.ForeignKey(ProductFlavor, on_delete=models.CASCADE, related_name="product_flavor")

    def __str__(self):
        return f'{self.spec.product.name} {self.localized_flavor_name}'


class FlavorImage(models.Model):
    name = models.CharField(max_length=20)
    image = models.ImageField(upload_to='photos/shop/%Y/%m/%d')

    spec = models.ForeignKey(ProductFlavor, on_delete=models.CASCADE, related_name="spec_image")

    def __str__(self):
        return f'{self.spec.product.name} : {self.name}'


class ProductAdvantage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_advantage")
    info = models.CharField(max_length=50)
    language = models.CharField(max_length=20, choices=Language.choices)

    def __str__(self):
        return f'{self.product.name} : {self.info}, lang: {self.language}'


class ProductFunction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_function")
    info = models.CharField(max_length=50)
    language = models.CharField(max_length=20, choices=Language.choices)

    def __str__(self):
        return f'{self.product.name} : {self.info}, lang: {self.language}'


class ProductUse(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_use")
    info = models.CharField(max_length=50)
    language = models.CharField(max_length=20, choices=Language.choices)

    def __str__(self):
        return f'{self.product.name} : {self.info}, lang: {self.language}'


# all products : Product join ProductInfo where lang=lang
#
# product/1 : Product join ProductInfo  join ProductImage where lang=lang
#

class ProductInfo(models.Model):
    localized_info_name = models.CharField(max_length=20, unique=True, default="n1")

    description = models.TextField()

    language = models.CharField(max_length=20, choices=Language.choices)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_info")

    def __str__(self):
        return f'{self.product.name} : {self.language}'
