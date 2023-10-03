from django.contrib import admin
from .models import CustomUser, Image

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Image)