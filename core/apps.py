<<<<<<< HEAD
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
=======
import firebase_admin
from firebase_admin import credentials
from django.apps import AppConfig
from django.conf import settings
import os

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        cred_path = os.path.join(settings.BASE_DIR, 'firebase_credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
>>>>>>> 94da046 (Fiz o calendário e a api pagamento)
