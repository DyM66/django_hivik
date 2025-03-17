# ntf/signals.py
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.text import Truncator
from django.utils import timezone
from inv.models import Solicitud