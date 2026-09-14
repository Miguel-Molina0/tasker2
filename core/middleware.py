from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from core.models import Usuario
from urllib.parse import parse_qs

@database_sync_to_async
def get_user_from_token(token_key)
    try:
        access_token = AcessToken(token_key)
        user_id = access_token['user_id']
        return Usuario.objects.get(id=user_id)
    except exceptions:
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__self(self, inner):
        self.inner = inner
    
    async def __call__(self, scope, receive, send):
        query_string = parse_qs(cope.get('query_string', b'').decode('utf-8'))
        token = query_string.get('token', [None])[0]

        if token:
            scope['user'] =  await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await self.iner(scope, receive, send)
