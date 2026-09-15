from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from .views import (
<<<<<<< HEAD
    CategoriaViewSet, MensagemViewSet, UsuarioViewSet, AnuncioViewSet, 
=======
    AsaasWebhookView, CategoriaViewSet, MensagemViewSet, UsuarioViewSet, AnuncioViewSet, 
>>>>>>> 94da046 (Fiz o calendário e a api pagamento)
    ServicoViewSet, ContratacaoViewSet, PagamentoViewSet, CalendarioViewSet, 
    ChatViewSet, AvaliacaoViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'anuncios', AnuncioViewSet)
router.register(r'avaliacao', AvaliacaoViewSet, basename='avaliacao')
router.register(r'servicos', ServicoViewSet)
router.register(r'contratacoes', ContratacaoViewSet, basename='contratacao')
router.register(r'categorias', CategoriaViewSet)
router.register(r'pagamentos', PagamentoViewSet)
router.register(r'calendarios', CalendarioViewSet)
router.register(r'chats', ChatViewSet)
router.register(r'mensagens', MensagemViewSet, basename='mensagem')

urlpatterns = [
    path('', include(router.urls)),
<<<<<<< HEAD
=======
    path('api/webhooks/asaas/', AsaasWebhookView.as_view(), name='asaas-webhook'),
>>>>>>> 94da046 (Fiz o calendário e a api pagamento)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)