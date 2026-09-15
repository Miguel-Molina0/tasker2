import requests
from django.conf import settings

class AsaasService:
    def __init__(self):
        self.headers = {
            "access_token": settings.ASAAS_API_KEY,
            "Content-Type": "application/json"
        }
        self.url = settings.ASAAS_API_URL

    def criar_cliente(self, usuario):
        """Cria ou recupera um cliente no Asaas."""
        payload = {
            "name": usuario.username,
            "cpfCnpj": usuario.nr_cpf or "",
            "email": usuario.email,
            "mobilePhone": usuario.nr_telefone or ""
        }
        response = requests.post(f"{self.url}/customers", json=payload, headers=self.headers)
        return response.json()

    def criar_cobranca(self, cliente_id_asaas, valor, descricao):
        """Gera uma cobrança PIX/Boleto retida para a contratação."""
        payload = {
            "customer": cliente_id_asaas,
            "billingType": "UNDEFINED",  # Permite Pix, Boleto ou Cartão na tela do Asaas
            "value": float(valor),
            "dueDate": "2026-12-31",      # Ajuste dinamicamente conforme necessário
            "description": descricao
        }
        response = requests.post(f"{self.url}/payments", json=payload, headers=self.headers)
        return response.json()

    def transferir_para_prestador(self, valor, chave_pix_prestador):
        """Transfere os valores retidos para a conta Pix do prestador após a conclusão."""
        payload = {
            "value": float(valor),
            "pixAddressKey": chave_pix_prestador,
            "pixAddressKeyType": "EVP",  # Opções: CPF, CNPJ, EMAIL, PHONE, EVP
            "description": "Repasse referente à conclusão do serviço"
        }
        response = requests.post(f"{self.url}/transfers", json=payload, headers=self.headers)
        return response.json()