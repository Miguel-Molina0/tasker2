from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from firebase_admin import messaging

@shared_task
def enviar_email_noticacao(email_destino, assunto, mensagem):
    send_mail(
        subject=assunto,
        message=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email_destino],
        fail_silently=True,
    )

@shared_task
def enviar_push_fcm(fcm_token, titulo, corpo, dados_extras=None):
    if not fcm_token:
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=titulo,
            body=corpo,
        ),
        token=fcm_token,
        data=dados_extras or {},
    )
    try:
        messaging.send(message)
    except Exception as e:
        print(f"Erro ao enviar notificação FCM: {e}")
