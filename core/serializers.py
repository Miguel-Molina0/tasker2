from rest_framework import serializers
from django.db.models import Avg
from .models import Categoria, Contratacao, Mensagem, Servico, Usuario, Anuncio, Pagamento, Chat, Calendario, Avaliacao

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'password', 
            'nr_cpf', 'nr_telefone', 'ds_biografia', 
            'tp_foto', 'id_tp_perfil'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


class AnuncioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anuncio
        fields = '__all__'

    
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class ServicoSerializer(serializers.ModelSerializer):
    categorias_detalhes = CategoriaSerializer(source='categorias', many=True, read_only=True)
    
    class Meta:
        model = Servico
        fields = '__all__'


class ContratacaoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source='fk_id_cliente.username', read_only=True)
    anuncio_titulo = serializers.CharField(source='fk_id_anuncio.nm_titulo', read_only=True)
    prestador_id = serializers.IntegerField(source='fk_id_anuncio.usuario.id', read_only=True)

    class Meta:
        model = Contratacao
        fields = [
            'id', 
            'fk_id_cliente', 
            'cliente_nome',
            'fk_id_anuncio', 
            'anuncio_titulo', 
            'prestador_id',
            'st_status', 
            'dt_criacao', 
            'dt_atualizacao'
        ]
        read_only_fields = ['fk_id_cliente', 'st_status', 'dt_criacao', 'dt_atualizacao']

    def validate(self, data):
        user = self.context['request'].user
        anuncio = data.get('fk_id_anuncio')

        if anuncio and anuncio.usuario == user:
            raise serializers.ValidationError("Você não pode contratar o seu próprio serviço.")
        return data


class PagamentoSerializer(serializers.ModelSerializer):
    status_contratacao = serializers.CharField(source='fk_id_contratacao.st_status', read_only=True)

    class Meta:
        model = Pagamento
        fields = '__all__'


class CalendarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendario
        fields = '__all__'


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = '__all__'  


class AvaliacaoSerializer(serializers.ModelSerializer):
    avaliador_nome = serializers.CharField(source='avaliador.username', read_only=True)
    avaliado_nome = serializers.CharField(source='avaliado.username', read_only=True)
    media_avaliacoes = serializers.SerializerMethodField()

    class Meta:
        model = Avaliacao
        fields = [
            'id',
            'fk_id_contratacao',
            'avaliador',
            'avaliador_nome',
            'avaliado',
            'avaliado_nome',
            'nr_nota',
            'ds_comentario',
            'dt_criacao',
            'media_avaliacoes'
        ]
        read_only_fields = ['avaliador', 'avaliado', 'dt_criacao']

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        contratacao = data.get('fk_id_contratacao')

        if contratacao.st_status != 'CONCLUIDO':
            raise serializers.ValidationError(
                "Não é possível avaliar um serviço que ainda não foi concluído."
            )

        eh_cliente = (contratacao.fk_id_cliente == user)
        eh_prestador = (contratacao.fk_id_anuncio.usuario == user)

        if not (eh_cliente or eh_prestador):
            raise serializers.ValidationError(
                "Você não tem permissão para avaliar esta contratação."
            )

        if hasattr(contratacao, 'avaliacao'):
            raise serializers.ValidationError(
                "Esta contratação já foi avaliada."
            )

        return data

    def get_media_avaliacoes(self, obj):
        media = Avaliacao.objects.filter(avaliado=obj.avaliado).aggregate(Avg('nr_nota'))['nr_nota__avg']
        return round(media, 1) if media else 0.0


class MensagemSerializer(serializers.ModelSerializer):
    remetente_username = serializers.CharField(source='remetente.username', read_only=True)

    class Meta:
        model = Mensagem
        fields = ['id', 'fk_id_contratacao', 'remetente', 'remetente_username', 'ds_mensagem', 'dt_envio']
        read_only_fields = ['remetente', 'dt_envio']