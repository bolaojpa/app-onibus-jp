import requests
import sys
from bs4 import BeautifulSoup
import json
import time
import sqlite3
from dotenv import load_dotenv

load_dotenv()

def raspar_dados_linhas(url):
    # (Esta função permanece a mesma)
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

        dados_horario["nome"] = soup.find('h2').text.strip().split('\n')[0] if soup.find('h2') else "Nome não encontrado"

        dias_da_semana = soup.find_all('div', class_='col-xl-4 col-lg-6 col-md-6 col-sm-12 mb-3')
        for dia in dias_da_semana:
            dia_semana = dia.find('strong').text.split(' | ')[0] if dia.find('strong') else None
            if dia_semana:
                horarios = [h.text.strip() for h in dia.find_all('span', class_='badge badge-secondary badge-legenda-a')]
                dados_horario[dia_semana.lower()] = horarios

        observacoes = []
        for strong_tag in soup.find_all('strong'):
            if strong_tag.text.strip().lower() == "observações:":
                pai = strong_tag.parent
                if pai:
                    for p_tag in pai.find_all('p'):
                        observacoes.append(p_tag.text.strip())
                break # Importante: sai do loop após encontrar as observações

        dados_horario["observacao"] = "\n".join(observacoes).strip()

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar {url_horario}: {e}")
        return None
    except AttributeError as e:
        print(f"Erro de atributo ao processar HTML em {url_horario}: {e}")
        print(soup)
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar horarios em {url_horario}: {e}")
        return None

    return dados_horario

def completar_links(dados, url_base="https://servicos.semobjp.pb.gov.br"):
    for linha in dados:
        if linha and linha.get("itinerario_link"):
            if not linha['itinerario_link'].startswith("http"):
                linha["itinerario_link"] = url_base + linha["itinerario_link"]
            if linha.get("horario_link"):
                if not linha['horario_link'].startswith("http"):
                    linha["horario_link"] = url_base + linha["horario_link"]
    return dados

def criar_tabela_linhas(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS linhas (
                codigo TEXT PRIMARY KEY,
                itinerario_link TEXT,
                horario_link TEXT,
                nome TEXT,
                horarios TEXT,
                observacao TEXT
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela: {e}")

def salvar_dados_bd(conn, dados):
    try:
        cursor = conn.cursor()
        for linha in dados:
            horarios_json = json.dumps(linha.get("horarios"), ensure_ascii=False) if linha.get("horarios") else None
            cursor.execute("""
                INSERT OR REPLACE INTO linhas (codigo, itinerario_link, horario_link, nome, horarios, observacao)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (linha["codigo"], linha.get("itinerario_link"), linha.get("horario_link"), linha.get("horarios",{}).get("nome"), horarios_json, linha.get("horarios",{}).get("observacao")))
        conn.commit()
        print("Dados salvos no banco de dados.")
    except sqlite3.Error as e:
        print(f"Erro ao inserir dados no banco de dados: {e}")

def main():
    url_base = "https://servicos.semobjp.pb.gov.br/linhas-de-onibus/"
    todas_as_linhas = []
    page = 1
    max_pages = None

    conn = sqlite3.connect('onibus.db')
    criar_tabela_linhas(conn)

    try:
        response = requests.get(url_base)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        paginacao = soup.find("ul", class_="pagination")
        if paginacao:
            links_paginacao = paginacao.find_all("a")
            if links_paginacao:
                # Encontra o último link numérico (penúltimo elemento da lista)
                ultimo_link = links_paginacao[-2].text.strip()
                try:
                    max_pages = int(ultimo_link)
                except ValueError:
                    print("Não foi possível determinar o número máximo de páginas. Usando valor padrão (10).")
                    max_pages = 10
            else:
                max_pages = 1  # Se não houver links de paginação, assume apenas uma página
        else:
            max_pages = 1  # Se não houver elemento de paginação, assume apenas uma página
    except requests.exceptions.RequestException:
        print("Erro ao obter o número máximo de páginas. Usando valor padrão (10).")
        max_pages = 10
    except AttributeError:
        print("Erro ao obter o número máximo de páginas. Usando valor padrão (10).")
        max_pages = 10
    except:
        print("Erro ao obter o número máximo de páginas. Usando valor padrão (10).")
        max_pages = 10

    if max_pages is None:
        max_pages = 10
    
    print(f"Número máximo de páginas: {max_pages}")

    while page <= max_pages:
        url = f"{url_base}?page={page}" if page > 1 else url_base
        print(f"Raspando página de linhas: {url}")
        data_linhas = raspar_dados_linhas(url)

        if data_linhas is None:
            print(f"Falha ao raspar a página {page} de linhas.")
            break
        elif not data_linhas:
            print(f"Página {page} de linhas vazia. Fim da raspagem de linhas.")
            break

        data_completos = completar_links(data_linhas)

        for linha in data_completos:
            if linha and linha.get("horario_link"):
                print(f"Raspando horários da linha: {linha['codigo']}")
                dados_horarios = buscar_dados_horarios(linha['horario_link'])
                linha["horarios"] = dados_horarios
                time.sleep(1)
            else:
                print(f"Link de horário não encontrado ou linha inválida para a linha: {linha.get('codigo') if linha else 'Linha não encontrada'}")
        todas_as_linhas.extend(data_completos)
        page += 1
        time.sleep(1)

    salvar_dados_bd(conn, todas_as_linhas)
    conn.close()

if __name__ == "__main__":
    main()