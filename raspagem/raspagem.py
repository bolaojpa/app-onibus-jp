import requests
from bs4 import BeautifulSoup
import json
import time
import os

# ... (Código da função raspar_dados e salvar_dados da resposta anterior)

if __name__ == "__main__":
    dados = raspar_dados()
    salvar_dados(dados, "dados_onibus.json") # Salva na raiz do repositorio