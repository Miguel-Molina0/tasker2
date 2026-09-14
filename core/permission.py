from rest_framework import permissions

class IsParticipanteContratacao(permissions.BasePermission):
    """
    Permissão que concede acesso apenas se o usuário logado for
    o contratante ou o prestador/anunciante associado à contratação.
    """

    def has_object_permission(self, request, view, obj):
        contratacao = getattr(obj, 'fk_id_contratacao', None)
        if contratacao:
            usuario_logado = request.user
            eh_contratante = (contratacao.fk_id_cliente == usuario_logado)
            eh_prestador = (contratacao.fk_id_anuncio.usuario == usuario_logado)
            
            return eh_contratante or eh_prestador

        return False