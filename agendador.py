import schedule
import time
import subprocess
import sys
import logging
from datetime import datetime

# Configuração do logging para o agendador (arquivo separado)
logging.basicConfig(filename='agendador.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def executar_raspagem():
    try:
        logging.info("Iniciando a raspagem e atualização do banco de dados...")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando a raspagem e atualização do banco de dados...")

        python_executable = sys.executable
        subprocess.run([python_executable, "raspagem.py"], check=True, capture_output=True, text=True) # Captura a saída do subprocesso

        # Salva a data e hora da última atualização.
        now = datetime.now()
        data_hora_formatada = now.strftime("%d/%m/%Y %H:%M:%S")

        with open("last_update.txt", "w") as f:
            f.write(data_hora_formatada)

        logging.info(f"Raspagem e atualização concluídas com sucesso. Data e hora gravadas em last_update.txt: {data_hora_formatada}")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Raspagem e atualização concluídas com sucesso. Data e hora gravadas em last_update.txt: {data_hora_formatada}")

    except subprocess.CalledProcessError as e:
        error_message = f"Erro durante a execução da raspagem: {e}\nSaída do subprocesso:\n{e.stderr}" # Inclui a saída de erro do subprocesso
        logging.error(error_message) #Usando log para registrar os erros
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Erro durante a execução da raspagem:")
        print(e)
        print(f"Stderr: {e.stderr}")

        now = datetime.now()
        data_hora_formatada = now.strftime("%d/%m/%Y %H:%M:%S")
        with open("last_update.txt", "w") as f:
            f.write(f"{data_hora_formatada} (Erro na raspagem)")
        print(f"Data e hora da tentativa de raspagem com erro gravadas em last_update.txt: {data_hora_formatada}")

    except Exception as e:
        error_message = f"Um erro inesperado ocorreu: {e}"
        logging.exception(error_message)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Um erro inesperado ocorreu:")
        print(e)

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

# A cada 1 minuto (para testes - DESATIVAR EM PRODUÇÃO):
schedule.every(1).minutes.do(executar_raspagem)

logging.info("Agendador iniciado. Aguardando a próxima execução...") #log para quando o agendador inicia
print("Agendador iniciado. Aguardando a próxima execução...")

while True:
    schedule.run_pending()
    time.sleep(1)