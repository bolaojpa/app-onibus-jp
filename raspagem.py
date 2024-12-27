import requests
from bs4 import BeautifulSoup
import json
import time

def raspar_dados(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    tabela = soup.find("table", class_="table")
    dados = []

    if tabela:
        tbody = tabela.find("tbody")
        if tbody:
            linhas = tbody.find_all("tr")
            for linha in linhas:
                celulas = linha.find_all("td")
                if celulas:
                    codigo = celulas[0].text
                    itinerario = celulas[1].find("a")
                    horario = celulas[2].find("a")

                    dados.append({
                        "codigo": codigo.strip(),
                        "itinerario_link": itinerario["href"] if itinerario else None,
                        "horario_link": horario["href"] if horario else None
                    })
    return dados

def completar_links(dados, url_base="https://servicos.semobjp.pb.gov.br"):
    for linha in dados:
        if linha["itinerario_link"]:
            linha["itinerario_link"] = url_base + linha["itinerario_link"]
        if linha["horario_link"]:
            linha["horario_link"] = url_base + linha["horario_link"]
    return dados

def salvar_dados(dados, nome_arquivo="todas_as_linhas_onibus.json"):
    with open(nome_arquivo, "w", encoding='utf-8') as outfile:
        json.dump(dados, outfile, indent=4, ensure_ascii=False)

def main():
    url_base = "https://servicos.semobjp.pb.gov.br/linhas-de-onibus/"
    todas_as_linhas = []
    page = 1

    while True:
        url = f"{url_base}?page={page}" if page > 1 else url_base
        print(f"Raspando página: {url}")
        data = raspar_dados(url)
        if data:
            if not data:
                print(f"Página {page} vazia. Fim da raspagem.")
                break
            data_completos = completar_links(data)
            todas_as_linhas.extend(data_completos)
            page += 1
            time.sleep(1)
        else:
            print(f"Falha ao raspar a página {page}. Fim da raspagem.")
            break

    salvar_dados(todas_as_linhas)

if __name__ == "__main__":
    main()