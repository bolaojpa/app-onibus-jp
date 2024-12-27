import requests
from bs4 import BeautifulSoup
import json
import time

def raspar_dados_linhas(url):
    """Raspagem dos dados das linhas de ônibus (código, links)."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        tabela = soup.find("table", class_="table")
        dados = []
        if tabela:
            tbody = tabela.find("tbody")
            if tbody:
                linhas = tbody.find_all("tr")
                for linha in linhas:
                    celulas = linha.find_all("td")
                    if celulas and len(celulas) == 3:
                        codigo = celulas[0].text.strip()
                        itinerario = celulas[1].find("a")
                        horario = celulas[2].find("a")
                        dados.append({
                            "codigo": codigo,
                            "itinerario_link": itinerario["href"] if itinerario else None,
                            "horario_link": horario["href"] if horario else None
                        })
            else:
                print(f"<tbody> não encontrado em {url}")
        else:
            print(f"Tabela não encontrada em {url}")
        return dados
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar {url}: {e}")
        return None
    except AttributeError as e:
        print(f"Erro de atributo ao processar HTML em {url}: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado em raspar_dados_linhas {url}: {e}")
        return None

def buscar_dados_horarios(url_horario):
    """Busca os dados de horários de uma linha de ônibus, usando "Observações:" como âncora."""
    dados_horario = {}
    try:
        response = requests.get(url_horario)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        dados_horario["nome"] = soup.find('h2').text.strip().split('\n')[0]
        dias_da_semana = soup.find_all('div', class_='col-xl-4 col-lg-6 col-md-6 col-sm-12 mb-3')
        for dia in dias_da_semana:
            dia_semana = dia.find('strong').text.split(' | ')[0]
            horarios = [h.text.strip() for h in dia.find_all('span', class_='badge badge-secondary badge-legenda-a')]
            dados_horario[dia_semana.lower()] = horarios

        for strong_tag in soup.find_all('strong'):
            if strong_tag.text.strip().lower() == "observações:":
                observacoes = []
                pai = strong_tag.parent
                if pai:
                    for p_tag in pai.find_all('p'):
                        observacoes.append(p_tag.text.strip())
                if observacoes:
                    dados_horario["observacao"] = "\n".join(observacoes)
                break

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar {url_horario}: {e}")
        return None
    except AttributeError as e:
        print(f"Erro de atributo ao processar HTML em {url_horario}: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar horarios em {url_horario}: {e}")
        return None

    return dados_horario

def completar_links(dados, url_base="https://servicos.semobjp.pb.gov.br"):
    for linha in dados:
        if linha["itinerario_link"]:
            linha["itinerario_link"] = url_base + linha["itinerario_link"]
        if linha["horario_link"]:
            linha["horario_link"] = url_base + linha["horario_link"]
    return dados

def salvar_dados(dados, nome_arquivo="todas_as_linhas_onibus.json"):
    try:
        with open(nome_arquivo, "w", encoding='utf-8') as outfile:
            json.dump(dados, outfile, indent=4, ensure_ascii=False)
        print(f"Dados salvos em {nome_arquivo}")
    except Exception as e:
        print(f"Erro ao salvar dados: {e}")

def main():
    url_base = "https://servicos.semobjp.pb.gov.br/linhas-de-onibus/"
    todas_as_linhas = []
    page = 1

    while True:
        url = f"{url_base}?page={page}" if page > 1 else url_base
        print(f"Raspando página de linhas: {url}")
        data_linhas = raspar_dados_linhas(url)
        if data_linhas is None:
            print(f"Falha ao raspar a página {page} de linhas. Fim da raspagem.")
            break
        elif not data_linhas:
            print(f"Página {page} de linhas vazia. Fim da raspagem de linhas.")
            break
        
        data_completos = completar_links(data_linhas)
        for linha in data_completos:
            if linha.get("horario_link"):
                print(f"Raspando horários da linha: {linha['codigo']}")
                dados_horarios = buscar_dados_horarios(linha['horario_link'])
                linha["horarios"] = dados_horarios
                time.sleep(1)
            else:
                print(f"Link de horário não encontrado para a linha: {linha['codigo']}")
        todas_as_linhas.extend(data_completos)
        page += 1
        time.sleep(1)

    salvar_dados(todas_as_linhas)

if __name__ == "__main__":
    main()