import django_filters
<<<<<<< HEAD
=======
from django.db.models import F
from django.db.models.functions import Cos, Sin, Radians, ACos
>>>>>>> 94da046 (Fiz o calendário e a api pagamento)
from .models import Anuncio

class AnuncioFilter(django_filters.FilterSet):
    preco_min = django_filters.NumberFilter(field_name='vl_preco', lookup_expr='gte')
<<<<<<< HEAD
    
    preco_max = django_filters.NumberFilter(field_name='vl_preco', lookup_expr='lte')

    class Meta:
        model = Anuncio
        fields = ['fk_id_categoria', 'fk_id_usuario', 'preco_min', 'preco_max']
=======
    preco_max = django_filters.NumberFilter(field_name='vl_preco', lookup_expr='lte')
    
    # Filtros virtuais que acionam a função de geolocalização
    latitude = django_filters.NumberFilter(method='filtrar_por_distancia')
    longitude = django_filters.NumberFilter(method='filtrar_por_distancia')
    raio_km = django_filters.NumberFilter(method='filtrar_por_distancia')

    class Meta:
        model = Anuncio
        fields = ['fk_id_categoria', 'fk_id_usuario', 'preco_min', 'preco_max']

    def filtrar_por_distancia(self, queryset, name, value):
        # Captura os dados enviados na requisição GET
        lat = self.data.get('latitude')
        lon = self.data.get('longitude')
        raio = self.data.get('raio_km', 15)  # Padrão de 15km se não for informado

        if lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)
                raio = float(raio)

                # Evita erros se o banco de dados contiver anúncios sem coordenada registrada
                queryset = queryset.exclude(nr_latitude__isnull=True, nr_longitude__isnull=True)

                # Converte as coordenadas do banco e da pesquisa para radianos
                radlat = Radians(lat)
                radlon = Radians(lon)
                rad_anuncio_lat = Radians(F('nr_latitude'))
                rad_anuncio_lon = Radians(F('nr_longitude'))

                # Raio médio da Terra = 6371 km
                # Aplicação da Fórmula de Haversine via ORM do Django
                queryset = queryset.annotate(
                    distancia_km=6371 * ACos(
                        Cos(radlat) * Cos(rad_anuncio_lat) * Cos(rad_anuncio_lon - radlon) +
                        Sin(radlat) * Sin(rad_anuncio_lat)
                    )
                ).filter(distancia_km__lte=raio).order_by('distancia_km')
            except ValueError:
                pass # Ignora caso as coordenadas venham mal formatadas

        return queryset
>>>>>>> 94da046 (Fiz o calendário e a api pagamento)
