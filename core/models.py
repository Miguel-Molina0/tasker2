from django.db import models
from django.conf import settings  # pyright: ignore[reportMissingImports]
from django.contrib.auth.models import AbstractUser  
from django.core.validators import MinValueValidator, MaxValueValidator

class Usuario(AbstractUser):
    PERFIL_CHOICES = [
        ('autonomo', 'Autônomo'),
        ('contratante', 'Contratante'),
    ]
    
    nr_cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    nr_telefone = models.CharField(max_length=15, null=True, blank=True)
    ds_biografia = models.TextField(blank=True, null=True)
    tp_foto = models.ImageField(upload_to='perfis/', blank=True, null=True)
    id_tp_perfil = models.CharField(max_length=15, choices=PERFIL_CHOICES, default='contratante')
    fcm_token = models.CharField(max_length=255, blank=True, null=True)  
    asaas_customer_id = models.CharField(max_length=80, blank=True, null=True)
    chave_pix = models.CharField(max_length=100, blank=True, null=True)


    def __str__(self):
        return self.username

class Categoria(models.Model):
    nm_categoria = models.CharField(max_length=45)

    def __str__(self):
        return self.nm_categoria


class Anuncio(models.Model):
    nm_titulo = models.CharField(max_length=50)
    nm_descricao = models.CharField(max_length=150)
    vl_preco = models.DecimalField(max_digits=10, decimal_places=2)
    nm_area_atendimento = models.CharField(max_length=100)
    nm_disponibilidade = models.CharField(max_length=45)
    st_anuncio = models.BooleanField(default=True) # Substituindo o tinyint por Boolean
    fk_id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fk_id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    dt_criacao_anuncio = models.DateTimeField(auto_now_add=True)


class Servico(models.Model):
    nm_servico = models.CharField(max_length=100)
    ds_servico = models.TextField(blank=True, null=True)
    fk_id_anuncio = models.ForeignKey(Anuncio, on_delete=models.CASCADE)
    fk_id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    
    categorias = models.ManyToManyField(Categoria, related_name='servicos')

class Contratacao(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('ACEITO', 'Aceito'),
        ('RECUSADO', 'Recusado'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    fk_id_cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='contratacoes_cliente'
    )
    fk_id_anuncio = models.ForeignKey(
        'Anuncio', 
        on_delete=models.CASCADE, 
        related_name='contratacoes_anuncio'
    )
    st_status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='PENDENTE'
    )
    concluido_cliente =  models.BooleanField(default=False)
    concluido_prestador = models.BooleanField(default=False)    

    dt_criacao = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)
<<<<<<< HEAD

=======
    dt_agendamento = models.DateField(null=True, blank=True)
    hr_inicio = models.TimeField(null=True, blank=True)
    hr_final = models.TimeField(null=True, blank=True)
    nr_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    nr_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
>>>>>>> 94da046 (Fiz o calendário e a api pagamento)
    def __str__(self):
        return f"Contratação #{self.id} - {self.fk_id_anuncio.nm_titulo} ({self.st_status})"

class Pagamento(models.Model):
    STATUS_PAGAMENTO = [
        ('retido', 'Retido'),
        ('liberado', 'Liberado'),
        ('bloqueado', 'Bloqueado'),
    ]

    vl_servico = models.DecimalField(max_digits=10, decimal_places=2)
    nm_token_api = models.CharField(max_length=150, blank=True, null=True)
    st_pagamento = models.CharField(max_length=15, choices=STATUS_PAGAMENTO)
    dt_declaracao_pagamento = models.DateTimeField(blank=True, null=True)
    fk_id_contratacao = models.ForeignKey(Contratacao, on_delete=models.CASCADE)

    asaas_payment_id = models.CharField(max_length=100, blank=True, null=True)
    pix_qr_code = models.TextField(blank=True, null=True)
    pix_copia_cola = models.TextField(blank=True, null=True)

class Calendario(models.Model):
    dt_agendamento = models.DateField()
    hr_inicio = models.TimeField()
    hr_final = models.TimeField()
    st_agendamento = models.CharField(max_length=45, blank=True, null=True)
    fk_id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fk_id_contratacao = models.ForeignKey(Contratacao, on_delete=models.CASCADE)


class Chat(models.Model):
    tx_mensagem = models.TextField()
    dt_envio = models.DateTimeField(auto_now_add=True) # Preenche a data/hora automaticamente ao enviar
    st_visualizacao = models.BooleanField(default=False)
    fk_id_remetente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensagens_enviadas')
    fk_id_destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensagens_recebidas')


class Avaliacao(models.Model):
    fk_id_contratacao = models.OneToOneField(
        'Contratacao',
        on_delete=models.CASCADE,
        related_name='avaliacao'
    )
    avaliador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avaliacoes_feitas'
    )
    avaliado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avaliacoes_recebidas'
    )
    nr_nota = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Nota de 1 a 5 estrelas"
    )
    ds_comentario = models.TextField(blank=True, null=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'

    def __str__(self):
        return f"Avaliação #{self.id} - Nota: {self.nr_nota} para {self.avaliado.username}"
    
class Mensagem(models.Model):
    fk_id_contratacao = models.ForeignKey('Contratacao', on_delete=models.CASCADE, related_name='mensagens')
    remetente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ds_mensagem = models.TextField()
    dt_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.remetente.username}: {self.ds_mensagem[:20]}"    
