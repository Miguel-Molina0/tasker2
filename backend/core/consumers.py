import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Mensagem, Contratacao

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Obtém o id_contratacao a partir da URL (ex: ws/chat/5/)
        self.contratacao_id = self.scope['url_route']['kwargs']['contratacao_id']
        self.room_group_name = f'chat_{self.contratacao_id}'

        # Adiciona o usuário ao grupo de transmissão dessa contratação
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Remove o usuário do grupo ao desconectar
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Recebe mensagem via WebSocket do cliente (React)
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        mensagem_texto = text_data_json['mensagem']
        remetente_id = text_data_json['remetente_id']

        # Salva a mensagem no banco de dados de forma assíncrona
        mensagem_obj = await self.salvar_mensagem(remetente_id, mensagem_texto)

        # Transmite a mensagem recebida para todos os participantes do grupo
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': mensagem_obj.id,
                'mensagem': mensagem_obj.ds_mensagem,
                'remetente_id': remetente_id,
                'dt_envio': str(mensagem_obj.dt_envio)
            }
        )

    # Manipulador para o evento 'chat_message'
    async def chat_message(self, event):
        # Envia os dados para a conexão WebSocket do navegador
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'mensagem': event['mensagem'],
            'remetente_id': event['remetente_id'],
            'dt_envio': event['dt_envio']
        }))

    @sync_to_async
    def salvar_mensagem(self, remetente_id, texto):
        contratacao = Contratacao.objects.get(id=self.contratacao_id)
        return Mensagem.objects.create(
            fk_id_contratacao=contratacao,
            remetente_id=remetente_id,
            ds_mensagem=texto
        )