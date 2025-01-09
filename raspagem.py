import requests
import time
import logging
from bs4 import BeautifulSoup
import json
import sqlite3
import re
from dotenv import load_dotenv
import os
import shutil
import datetime
import glob # Importe o módulo glob

load_dotenv()

# Configuração do logging
logging.basicConfig(filename='raspagem.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def raspar_com_retry(url, tentativas=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
    }
    for i in range(tentativas):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logging.error(f"Tentativa {i+1} falhou ao acessar {url}: {e}")
            if i < tentativas - 1:
                time.sleep(2**i)  # Backoff exponencial
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logging.error(f"Página não encontrada: {url}")
            elif response.status_code == 503:
                logging.error(f"Serviço indisponível: {url}")
            else:
                logging.error(f"Erro HTTP {response.status_code} ao acessar {url}: {e}")
            return None
        except Exception as e:
            logging.exception(f"Erro inesperado durante a raspagem: {e}")
            return None
    logging.error(f"Falhou após {tentativas} tentativas ao acessar {url}")
    return None

def raspar_dados_linhas(html_content):
    try:
        soup = BeautifulSoup(html_content, "html.parser")
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
                return dados
            else:
                logging.warning("<tbody> não encontrado na tabela.")
                return None
        else:
            logging.warning("Tabela não encontrada na página.")
            return None
    except AttributeError as e:
        logging.error(f"Erro de atributo ao processar HTML: {e}")
        return None
    except Exception as e:
        logging.exception(f"Erro inesperado em raspar_dados_linhas: {e}")
        return None

def buscar_dados_horarios(html_content):
    dados_horario = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        dias_da_semana = soup.find_all('div', class_='col-xl-4 col-lg-6 col-md-6 col-sm-12 mb-3')
        for dia in dias_da_semana:
            dia_semana = dia.find('strong').text.split(' | ')[0] if dia.find('strong') else None
            if dia_semana:
                horarios = [h.text.strip() for h in dia.find_all('span', class_='badge badge-secondary badge-legenda-a')]
                dados_horario[dia_semana.lower()] = horarios

        return dados_horario # Retorna APENAS os horários

    except AttributeError as e:
        logging.error(f"Erro de atributo ao processar HTML em buscar_dados_horarios: {e}")
        return None
    except Exception as e:
        logging.exception(f"Erro inesperado ao buscar horarios: {e}")
        return None
    
def buscar_observacao(html_content): # Nova função para buscar a observação
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        observacoes = []
        for strong_tag in soup.find_all('strong'):
            if strong_tag.text.strip().lower() == "observações:":
                pai = strong_tag.parent
                if pai:
                    for p_tag in pai.find_all('p'):
                        observacoes.append(p_tag.text.strip())
                break
        return "\n".join(observacoes).strip()
    except AttributeError as e:
        logging.error(f"Erro de atributo ao processar HTML em buscar_observacao: {e}")
        return None
    except Exception as e:
        logging.exception(f"Erro inesperado ao buscar observacao: {e}")
        return None

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
            """, (linha["codigo"], linha.get("itinerario_link"), linha.get("horario_link"), linha.get("nome"), horarios_json, linha.get("observacao"))) # Salva a observação separadamente
        conn.commit()
        print("Dados salvos no banco de dados.")
    except sqlite3.Error as e:
        print(f"Erro ao inserir dados no banco de dados: {e}")

def fazer_backup_sqlite():
    nome_arquivo_bd = 'onibus.db'
    data_atual = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    nome_arquivo_backup = f'backups/backup_onibus_{data_atual}.db'

    os.makedirs('backups', exist_ok=True)  # Cria o diretório se não existir

    try:
        conn = sqlite3.connect(nome_arquivo_bd)
        backup_conn = sqlite3.connect(nome_arquivo_backup)
        with backup_conn:
            conn.backup(backup_conn)
        backup_conn.close()
        conn.close()
        logging.info(f"Backup criado com sucesso: {nome_arquivo_backup}")
        print(f"Backup criado com sucesso: {nome_arquivo_backup}")

        manter_apenas_ultimos_backups("backups", 5)  # Mantém apenas os 5 backups mais recentes

    except sqlite3.Error as e:
        logging.error(f"Erro ao criar backup: {e}")
        print(f"Erro ao criar backup: {e}")
    except Exception as e:
        logging.exception(f"Erro ao criar backup: {e}")
        print(f"Erro ao criar backup: {e}")

def manter_apenas_ultimos_backups(diretorio, quantidade):
    try:
        arquivos = [os.path.join(diretorio, f) for f in os.listdir(diretorio) if os.path.isfile(os.path.join(diretorio, f))]
        arquivos.sort(key=os.path.getmtime)  # Ordena por data de modificação (mais antigos primeiro)
        arquivos_para_deletar = arquivos[:-quantidade]  # Seleciona os arquivos mais antigos para deletar

        for arquivo in arquivos_para_deletar:
            os.remove(arquivo)
            logging.info(f"Backup antigo deletado: {arquivo}")
            print(f"Backup antigo deletado: {arquivo}")

    except OSError as e:
         logging.error(f"Erro ao deletar backups antigos: {e}")
         print(f"Erro ao deletar backups antigos: {e}")
    except Exception as e:
        logging.exception(f"Erro ao deletar backups antigos: {e}")
        print(f"Erro ao deletar backups antigos: {e}")

def restaurar_backup_recente():
    try:
        lista_de_backups = glob.glob('backups/backup_onibus_*.db')
        if not lista_de_backups:
            logging.warning("Nenhum backup encontrado para restaurar.")
            print("Nenhum backup encontrado para restaurar.")
            return False

        backup_mais_recente = max(lista_de_backups, key=os.path.getctime)
        shutil.copy2(backup_mais_recente, 'onibus.db')
        logging.info(f"Banco de dados restaurado do backup: {backup_mais_recente}")
        print(f"Banco de dados restaurado do backup: {backup_mais_recente}")
        return True
    except OSError as e:
        logging.error(f"Erro ao restaurar backup: {e}")
        print(f"Erro ao restaurar backup: {e}")
        return False
    except Exception as e:
        logging.exception(f"Erro ao restaurar backup: {e}")
        print(f"Erro ao restaurar backup: {e}")
        return False

def main():
    url_base = "https://servicos.semobjp.pb.gov.br/linhas-de-onibus/"
    todas_as_linhas = []
    page = 1

    conn = sqlite3.connect('onibus.db')
    criar_tabela_linhas(conn)

    try:
        response = raspar_com_retry(url_base)
        if response:
            soup = BeautifulSoup(response.content, "html.parser")
            paginacao = soup.find("ul", class_="pagination")
            if paginacao:
                links_paginacao = paginacao.find_all("a")
                numeros_paginas = [int(link.text.strip()) for link in links_paginacao if re.match(r"\d+", link.text.strip())]
                max_pages = max(numeros_paginas) if numeros_paginas else 1
            else:
                max_pages = 1
        else:
            logging.error(f"Falha ao obter dados da URL base {url_base}. Impossível determinar o número de páginas.")
            max_pages = 1

    except Exception as e:
        logging.exception(f"Erro ao obter o número máximo de páginas: {e}")
        max_pages = 1
        logging.info("Tentando restaurar o backup mais recente...")
        print("Tentando restaurar o backup mais recente...")
        if restaurar_backup_recente():
            logging.info("Restauração do backup concluída com sucesso.")
            print("Restauração do backup concluída com sucesso.")
        else:
            logging.error("Falha ao restaurar o backup. Verifique os logs.")
            print("Falha ao restaurar o backup. Verifique os logs.")
        return

    logging.info(f"Número máximo de páginas: {max_pages}")

    while page <= max_pages:
        url = f"{url_base}?page={page}" if page > 1 else url_base
        logging.info(f"Raspando página de linhas: {url}")
        try:
            response = raspar_com_retry(url)
            if response:
                data_linhas = raspar_dados_linhas(response.content)
                if data_linhas is None:
                    logging.error(f"Falha ao raspar os dados das linhas da página {page}.")
                elif not data_linhas:
                    logging.info(f"Página {page} de linhas vazia. Fim da raspagem de linhas.")
                    break
                else:
                    data_completos = completar_links(data_linhas)

                    for linha in data_completos:
                        if linha and linha.get("horario_link"):
                            logging.info(f"Raspando horários da linha: {linha['codigo']}")
                            response_horario = raspar_com_retry(linha['horario_link'])
                            if response_horario:
                                dados_horarios = buscar_dados_horarios(response_horario.content)
                                observacao = buscar_observacao(response_horario.content)
                                linha["horarios"] = dados_horarios
                                linha["observacao"] = observacao
                                time.sleep(1)
                            else:
                                logging.error(f"Falha ao obter horários para a linha: {linha['codigo']}")
                        else:
                            logging.warning(f"Link de horário não encontrado ou linha inválida para a linha: {linha.get('codigo') if linha else 'Linha não encontrada'}")
                    todas_as_linhas.extend(data_completos)
            else:
                logging.error(f"Falha ao acessar a URL da página {page}: {url}")
        except Exception as e:
            logging.exception(f"Erro durante a raspagem da página: {e}")
            logging.info("Tentando restaurar o backup mais recente...")
            print("Tentando restaurar o backup mais recente...")
            if restaurar_backup_recente():
                logging.info("Restauração do backup concluída com sucesso.")
                print("Restauração do backup concluída com sucesso.")
            else:
                logging.error("Falha ao restaurar o backup. Verifique os logs.")
                print("Falha ao restaurar o backup. Verifique os logs.")
            break

        page += 1
        time.sleep(1)

    salvar_dados_bd(conn, todas_as_linhas)
    conn.close()
    fazer_backup_sqlite()
    logging.info("Raspagem concluída.")

if __name__ == "__main__":
    main()