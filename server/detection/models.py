import os
import uuid
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

def scramble_uploaded_filename(instance, filename):
    extension = filename.split(".")[-1]
    return "{}.{}".format(uuid.uuid4(),extension)

class UploadAlert(models.Model):
    image = models.ImageField("Fire capture", upload_to=scramble_uploaded_filename)
    user_ID = models.ForeignKey(Token, on_delete=models.CASCADE)
    alert_receiver = models.CharField(max_length=200, verbose_name="Notify email")
    location = models.CharField(max_length=200, verbose_name="Forest zone")
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Detected at")

    class Meta:
        verbose_name = "Fire alert"
        verbose_name_plural = "Fire alerts"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender,instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
