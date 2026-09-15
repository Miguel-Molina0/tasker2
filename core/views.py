from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q  
from .tasks import enviar_email_noticacao, enviar_push_fcm
from .asaas import AsaasService
from rest_framework.views import APIView
from .models import Calendario, Avaliacao, Mensagem, Pagamento, Chat, Categoria, Usuario, Anuncio, Servico, Contratacao
from .serializers import (
    MensagemSerializer, CalendarioSerializer, CategoriaSerializer, UsuarioSerializer, 
    AnuncioSerializer, ServicoSerializer, ContratacaoSerializer, ChatSerializer, 
    AvaliacaoSerializer, PagamentoSerializer
)
from .permission import IsParticipanteContratacao
from .filters import AnuncioFilter
from .pagination import AnuncioPagination
from  asgiref.sync import import async_to_sync
from channels.layers import get_channel_layer
from  asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.views import APIView
from django.utils import timezone

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        user = request.user 

        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        elif request.method in ['PUT', 'PATCH']:
            is_partial = True if request.method == 'PATCH' else False
            serializer = self.get_serializer(instance=user, data=request.data, partial=is_partial)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnuncioViewSet(viewsets.ModelViewSet):
    queryset = Anuncio.objects.all().order_by('dt_criacao_anuncio')
    serializer_class = AnuncioSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AnuncioFilter
    pagination_class = AnuncioPagination

    search_fields = ['nm_titulo', 'ds_anuncio']
    ordering_fields = ['vl_preco', 'dt_criacao_anuncio']
    ordering = ['dt_criacao_anuncio']

    def perform_create(self, serializer):
        serializer.save(fk_id_usuario=self.request.user)


class ServicoViewSet(viewsets.ModelViewSet):
    queryset = Servico.objects.all()
    serializer_class = ServicoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class CalendarioViewSet(viewsets.ModelViewSet):
    queryset = Calendario.objects.all()
    serializer_class = CalendarioSerializer


class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]


class AvaliacaoViewSet(viewsets.ModelViewSet):
    serializer_class = AvaliacaoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Avaliacao.objects.all().order_by('-dt_criacao')
        usuario_id = self.request.query_params.get('usuario_id', None)
        if usuario_id is not None:
            queryset = queryset.filter(avaliado_id=usuario_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        contratacao = serializer.validated_data.get('fk_id_contratacao')

        if contratacao.fk_id_cliente == user:
            avaliado = contratacao.fk_id_anuncio.usuario
        else:
            avaliado = contratacao.fk_id_cliente

        serializer.save(avaliador=user, avaliado=avaliado)


class PagamentoViewSet(viewsets.ModelViewSet):
    queryset = Pagamento.objects.all()
    serializer_class = PagamentoSerializer
    permission_classes = [IsAuthenticated]


class ContratacaoViewSet(viewsets.ModelViewSet):
    serializer_class = ContratacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Contratacao.objects.filter(
            Q(fk_id_cliente=user) | Q(fk_id_anuncio__usuario=user)
        ).order_by('-dt_criacao')

    def perform_create(self, serializer):
        serializer.save(fk_id_cliente=self.request.user)
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
        
    def perform_create(self, serializer):
        contratacao = serializer.save(fk_id_cliente=self.request.user)
        cliente = self.request.user
        asaas = AsaasService()

        if not cliente.asaas_customer_id:
            asaas_cliente = asaas.criar_cliente(cliente)
            cliente.asaas_customer_id = asaas_cliente.get('id')
            cliente.save()

        cobranca = asaas.criar_cobranca(
            cliente_id_asaas=cliente.asaas_customer_id,
            valor=contratacao.fk_id_anuncio.vl_preco,
            descricao=f"Contratação #{contratacao.id} - {contratacao.fk_id_anuncio.nm_titulo}"
        )

        Pagamento.objects.create(
            vl_servico=contratacao.fk_id_anuncio.vl_preco,
            st_pagamento='retido',
            fk_id_contratacao=contratacao,
            asaas_payment_id=cobranca.get('id')
        )


    @action(detail=True, methods=['patch'], url_path='aceitar')
    def aceitar(self, request, pk=None):
        contratacao = self.get_object()

        if contratacao.fk_id_anuncio.usuario != request.user:
            raise PermissionDenied("Apenas o prestador do serviço pode aceitar esta contratação.")
        
        if contratacao.st_status != 'PENDENTE':
            raise ValidationError(f"Não é possível aceitar uma contratação com status '{contratacao.st_status}'.")
 
        contratacao.st_status = 'ACEITO'
        contratacao.save()

        if contratacao.dt_agendamento and contratacao.hr_inicio and contratacao.hr_final:
            Calendario.objects.create(
                dt_agendamento=contratacao.dt_agendamento,
                hr_inicio=contratacao.hr_inicio,
                hr_final=contratacao.hr_final,
                st_agendamento='CONFIRMADO',
                fk_id_usuario=contratacao.fk_id_anuncio.usuario,
                fk_id_contratacao=contratacao
            )

            Calendario.objects.create(
                dt_agendamento=contratacao.dt_agendamento,
                hr_inicio=contratacao.hr_inicio,
                hr_final=contratacao.hr_final,
                st_agendamento='CONFIRMADO',
                fk_id_usuario=contratacao.fk_id_cliente,
                fk_id_contratacao=contratacao
            )

        return Response({
            'status': 'Contratação aceita e agendada automaticamente no calendário!',
            'dados': self.get_serializer(contratacao).data
        })
    @action(detail=True, methods=['patch'], url_path='recusar')
    def recusar(self, request, pk=None):
        contratacao = self.get_object()
        if contratacao.fk_id_anuncio.usuario != request.user:
            raise PermissionDenied("Apenas o prestador do serviço pode recusar esta contratação.")
        
        if contratacao.st_status != 'PENDENTE':
            raise ValidationError("Apenas solicitações pendentes podem ser recusadas.")

        contratacao.st_status = 'RECUSADO'
        contratacao.save()
        return Response({'status': 'Contratação recusada.'})

    @action(detail=True, methods=['patch'], url_path='concluir')
    def concluir(self, request, pk=None):
        contratacao = self.get_object()
        user = request.user
        
        if user != contratacao.fk_id_cliente and user != contratacao.fk_id_anuncio.usuario:
            raise PermissionDenied("Você não faz parte desta contratação.")

        if contratacao.st_status != 'ACEITO':
            raise ValidationError("Apenas serviços com status 'ACEITO' podem ser concluídos.")

        if user == contratacao.fk_id_cliente:
            contratacao.concluido_cliente = True
        elif user == contratacao.fk_id_anuncio.usuario:
            contratacao.concluido_prestador = True

        status_alterado = False
        if contratacao.concluido_cliente and contratacao.concluido_prestador
            contratacao.st_status = 'CONCLUIDO'
            status_alterado = True
        outro_usuario = contratacao.fk_id_anuncio.usuario if user == contratacao.fk_id_cliente else contratacao.fk_id_cliente

        if user == contratacao.fk_id_cliente:
            contratacao.concluido_cliente = True
        else:
            contratacao.concluido_prestador = True

        status_final = False
        if contratacao.concluido_cliente and contratacao.concluido_prestador:
            contratacao.st_status = 'CONCLUIDO'
            status_final = True

        pagamento = Pagamento.objects.filter(fk_id_contratacao=contratacao).first()
        if pagamento and pagamento.st_pagamento == 'retido':
            prestador = contratacao.fk_id_anuncio.usuario
            if prestador.chave_pix:
                asaas = AsaasService()
                # Transfere o valor retido para o prestador
                asaas.transferir_para_prestador(pagamento.vl_servico, prestador.chave_pix)
                pagamento.st_pagamento = 'liberado'
                pagamento.save()

        contratacao.save()
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{contratacao.id}',
            {
                'type' : 'status_notification',
                'mensagem' : f"Serviço confirmado como concluído por {user.username}.",
                'st_status' : contratacao.st_status,
                'concluido_cliente' : contratacao.concluido_cliente,
                'concluido_prestador' : contratacao.concluido_prestador,

            }
        )


        msg_retorno = "Serviço concluído!" if status_alertado else "Sua confirmação foi registrada. Aguardando a outra parte."

        assunto = f"Atualização na contratação #{contratacao.id}"
        if status_final:
            corpo_email = f"Olá {outro_usuario.username}, o serviço referente ao anúncio '{contratacao.fk_id_anuncio.nm_titulo}' foi concluído com sucesso! Você já pode realizar a avaliação do serviço."
        else:
            corpo_email = f"Olá {outro_usuario.username}, o usuário {user.username} confirmou a conclusão do serviço referente ao anúncio '{contratacao.fk_id_anuncio.nm_titulo}'. Aguardando sua confirmação para finalizar a contratação."
        enviar_email_noticacao.delay(outro_usuario.email, assunto, corpo_email)

        if outro_usuario.fcm_token:
            enviar_notificacao_fcm.delay(
                fcm_token=outro_usuario.fcm_token,
                titulo="Atualização na contratação",
                corpo=corpo_email,
                dados_extras={'contratacao_id': str(contratacao.id)}
            )

        msg_retorno = "Serviço concluído!" if status_final else "Sua confirmação foi registrada. Aguardando a outra parte."

        return Response({
            'status' : msg_retorno,
            'dados' : self.get_serializer(contratacao).data
        })

    @action(detail=True, methods=['patch'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        contratacao = self.get_object()
        user = request.user

        # 1. Valida se o usuário faz parte da contratação
        if user != contratacao.fk_id_cliente and user != contratacao.fk_id_anuncio.usuario:
            raise PermissionDenied("Você não tem permissão para cancelar esta contratação.")

        # 2. Impede cancelamento de serviços já finalizados ou recusados
        if contratacao.st_status in ['CONCLUIDO', 'CANCELADO', 'RECUSADO']:
            raise ValidationError(f"Não é possível cancelar um serviço que já está '{contratacao.st_status}'.")

        # 3. Atualiza o status
        contratacao.st_status = 'CANCELADO'
        contratacao.save()

        # 4. Remove os agendamentos do calendário para liberar o horário do prestador
        Calendario.objects.filter(fk_id_contratacao=contratacao).delete()

        # 5. Tratamento financeiro: bloqueia repasse de pagamento retido
        pagamento = Pagamento.objects.filter(fk_id_contratacao=contratacao).first()
        if pagamento and pagamento.st_pagamento == 'retido':
            pagamento.st_pagamento = 'bloqueado'
            pagamento.save()
            # (Aqui você poderia adicionar a chamada para a API do Asaas estornando o valor ao cliente)

        # 6. Identifica a outra parte para as notificações
        outro_usuario = contratacao.fk_id_anuncio.usuario if user == contratacao.fk_id_cliente else contratacao.fk_id_cliente

        # 7. Notificação via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{contratacao.id}',
            {
                'type': 'status_notification',
                'mensagem': f"A contratação foi CANCELADA por {user.username}.",
                'st_status': contratacao.st_status,
                'concluido_cliente': contratacao.concluido_cliente,
                'concluido_prestador': contratacao.concluido_prestador,
            }
        )

        # 8. Notificações Push e E-mail
        assunto = f"Serviço Cancelado: #{contratacao.id}"
        corpo = f"Olá {outro_usuario.username}, o serviço de '{contratacao.fk_id_anuncio.nm_titulo}' foi cancelado por {user.username}. A agenda foi liberada."
        
        enviar_email_notificacao.delay(outro_usuario.email, assunto, corpo)
        if outro_usuario.fcm_token:
            enviar_push_fcm.delay(outro_usuario.fcm_token, "Serviço Cancelado", corpo, {'contratacao_id': str(contratacao.id)})

        return Response({
            'status': 'Contratação cancelada com sucesso. Os horários foram liberados do calendário.',
            'dados': self.get_serializer(contratacao).data
        })
    
class AsaasWebhookView(APIView):
    permission_classes = [] # Webhook aberto para callback da API

    def post(self, request):
        event = request.data.get('event')
        payment_id = request.data.get('payment', {}).get('id')

        if event in ['PAYMENT_RECEIVED', 'PAYMENT_CONFIRMED']:
            pagamento = Pagamento.objects.filter(asaas_payment_id=payment_id).first()
            if pagamento:
                pagamento.dt_declaracao_pagamento = timezone.now()
                pagamento.save()

        return Response({'status': 'received'}, status=status.HTTP_200_OK)

class MensagemViewSet(viewsets.ModelViewSet):
    serializer_class = MensagemSerializer
    permission_classes = [IsAuthenticated, IsParticipanteContratacao]

    def get_queryset(self):
        user = self.request.user
        queryset = Mensagem.objects.filter(
            Q(fk_id_contratacao__fk_id_cliente=user) | 
            Q(fk_id_contratacao__fk_id_anuncio__usuario=user)
        ).order_by('dt_envio')
        contratacao_id = self.request.query_params.get('contratacao', None)
        if contratacao_id is not None:
            queryset = queryset.filter(fk_id_contratacao_id=contratacao_id)

        return queryset

    def perform_create(self, serializer):
        contratacao = serializer.validated_data.get('fk_id_contratacao')
        user = self.request.user

        eh_cliente = (contratacao.fk_id_cliente == user)
        eh_prestador = (contratacao.fk_id_anuncio.usuario == user)

        if not (eh_cliente or eh_prestador):
            raise PermissionDenied("Você não tem permissão para enviar mensagens nesta contratação.")

        serializer.save(remetente=user)
