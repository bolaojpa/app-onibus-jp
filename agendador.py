import schedule
import time
import subprocess
import sys
from datetime import datetime
import os

def executar_raspagem():
    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando a raspagem e atualização do banco de dados...")

        # Obtém o caminho do executável Python atual para garantir o uso do ambiente virtual.
        python_executable = sys.executable
        subprocess.run([python_executable, "raspagem.py"], check=True)

        # Salva a data e hora da última atualização no arquivo last_update.txt.
        now = datetime.now()
        data_hora_formatada = now.strftime("%d/%m/%Y %H:%M:%S")

        # Usando 'with open' para garantir o fechamento correto do arquivo.
        with open("last_update.txt", "w") as f:
            f.write(data_hora_formatada)

        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Raspagem e atualização concluídas com sucesso. Data e hora gravadas em last_update.txt: {data_hora_formatada}")

    except subprocess.CalledProcessError as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Erro durante a execução da raspagem:")
        print(e)

        # Registra a tentativa de raspagem mesmo em caso de erro.
        now = datetime.now()
        data_hora_formatada = now.strftime("%d/%m/%Y %H:%M:%S")
        with open("last_update.txt", "w") as f:
            f.write(f"{data_hora_formatada} (Erro na raspagem)")
        print(f"Data e hora da tentativa de raspagem com erro gravadas em last_update.txt: {data_hora_formatada}")

    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Um erro inesperado ocorreu:")
        print(e)
        # Registra a tentativa de raspagem mesmo em caso de erro.
        now = datetime.now()
        data_hora_formatada = now.strftime("%d/%m/%Y %H:%M:%S")
        with open("last_update.txt", "w") as f:
            f.write(f"{data_hora_formatada} (Erro inesperado)")
        print(f"Data e hora da tentativa de raspagem com erro gravadas em last_update.txt: {data_hora_formatada}")



# Opções de agendamento (escolha apenas uma e descomente):

# A cada hora:
# schedule.every().hour.do(executar_raspagem)

# Diariamente às 03:00 da manhã:
# schedule.every().day.at("03:00").do(executar_raspagem)

# Toda segunda-feira às 06:00 da manhã (RECOMENDADO):
# schedule.every().monday.at("06:00").do(executar_raspagem)

# A cada 5 minutos (para testes - DESATIVAR EM PRODUÇÃO):
schedule.every(5).minutes.do(executar_raspagem)

print("Agendador iniciado. Aguardando a próxima execução...")

while True:
    schedule.run_pending()
    time.sleep(1)