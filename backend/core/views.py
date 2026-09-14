from rest_framework import viewsets
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly 
from .models import Calendario, Avaliacao, Mensagem, Pagamento, Chat, Categoria, Usuario, Anuncio, Servico, Contratacao
from .serializers import MensagemSerializer, CalendarioSerializer, CategoriaSerializer,UsuarioSerializer, AnuncioSerializer, ServicoSerializer, ContratacaoSerializer, ChatSerializer, AvaliacaoSerializer, PagamentoSerializer 
from .permission import IsParticipanteContratacao
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q  
from .filters import AnuncioFilter
from .pagination import AnuncioPagination
from core import permission

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

            serializer = self.get_serializer(
                instance=user, 
                data=request.data, 
                partial=is_partial  
            )

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        contratacao = serializer.validated_data.get('fk_id_contratacao')
        user = self.request.user

        eh_cliente = (contratacao.fk_id_cliente == user)
        eh_prestador = (contratacao.fk_id_anuncio.usuario == user)

        if not (eh_cliente or eh_prestador):
            raise PermissionDenied("Você não tem permissão para enviar mensagens nesta contratação.")

        serializer.save(remetente=user)

class AnuncioViewSet(viewsets.ModelViewSet):
    queryset = Anuncio.objects.all().order_by('dt_criacao_anuncio')
    serializer_class = AnuncioSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ['fk_id_categoria', 'fk_id_usuario']

    search_fields = ['nm_titulo', 'ds_anuncio']

    ordering_fields = ['vl_preco', 'dt_criacao_anuncio']
    ordering = ['dt_criacao_anuncio']  # Ordena por data de criação do anúncio por padrão

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class ServicoViewSet(viewsets.ModelViewSet):

    queryset = Servico.objects.all()
    serializer_class = ServicoSerializer

    permission_classes = [IsAuthenticatedOrReadOnly]

class ContratacaoViewSet(viewsets.ModelViewSet):

    queryset = Contratacao.objects.all()
    serializer_class = ContratacaoSerializer

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


    @action(detail=True, methods=['patch'], url_path='aceitar')
    def aceitar(self, request, pk=None):
        contratacao = self.get_object()
        if contratacao.fk_id_anuncio.usuario != request.user:
            raise PermissionDenied("Apenas o prestador do serviço pode aceitar esta contratação.")
        
        if contratacao.st_status != 'PENDENTE':
            raise ValidationError(f"Não é possível aceitar uma contratação com status '{contratacao.st_status}'.")

        contratacao.st_status = 'ACEITO'
        contratacao.save()
        return Response({'status': 'Contratação aceita com sucesso!', 'dados': self.get_serializer(contratacao).data})

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

        contratacao.st_status = 'CONCLUIDO'
        contratacao.save()
        return Response({'status': 'Serviço marcado como concluído!'})

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
        serializer.save(remetente=self.request.user)
    def perform_create(self, serializer):
        contratacao = serializer.validated_data.get('fk_id_contratacao')
        user = self.request.user

        eh_cliente = (contratacao.fk_id_cliente == user)
        eh_prestador = (contratacao.fk_id_anuncio.usuario == user)

        if not (eh_cliente or eh_prestador):
            raise PermissionDenied("Você não tem permissão para enviar mensagens nesta contratação.")

        serializer.save(remetente=user)