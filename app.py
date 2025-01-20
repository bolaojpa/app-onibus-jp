from flask import Flask, redirect, render_template, request, url_for, g, logging
import raspagem
import sqlite3
import os
import json
from urllib.parse import unquote

app = Flask(__name__)

DATABASE = 'onibus.db'

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), DATABASE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_table_if_not_exists():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
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
    finally:
        conn.close()

with app.app_context():
    create_table_if_not_exists()

@app.route("/", methods=['GET'])
def index():
    busca = request.args.get('busca')
    pagina = request.args.get('pagina', 1, type=int)
    linhas_por_pagina = 30

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if busca:
            cursor.execute("SELECT * FROM linhas WHERE nome LIKE ? OR codigo LIKE ?", ('%' + busca + '%', '%' + busca + '%',))
            linhas_totais = len(cursor.fetchall())
            cursor.execute("SELECT * FROM linhas WHERE nome LIKE ? OR codigo LIKE ? LIMIT ? OFFSET ?", ('%' + busca + '%', '%' + busca + '%', linhas_por_pagina, (pagina - 1) * linhas_por_pagina))
        else:
            cursor.execute("SELECT * FROM linhas")
            linhas_totais = len(cursor.fetchall())
            cursor.execute(f"SELECT * FROM linhas LIMIT {linhas_por_pagina} OFFSET {(pagina - 1) * linhas_por_pagina}")

        linhas = cursor.fetchall()
        num_paginas = (linhas_totais + linhas_por_pagina - 1) // linhas_por_pagina

    except sqlite3.Error as e:
        return f"Erro ao acessar o banco de dados: {e}"
    finally:
        conn.close()

    return render_template("index.html", linhas=linhas, busca=busca, pagina=pagina, num_paginas=num_paginas)

@app.route("/linha/<string:codigo>")
def detalhes_linha(codigo):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT codigo, nome, itinerario_link, horario_link FROM linhas WHERE codigo=?", (codigo,))
        linha = cursor.fetchone()
    except sqlite3.Error as e:
        return f"Erro ao acessar o banco de dados: {e}"
    finally:
        conn.close()
    return render_template("detalhes_linha.html", linha=linha)

@app.route("/horarios/<path:codigo>") # Use <path:codigo> aqui
def detalhes_horario(codigo):
    codigo = unquote(codigo) #Decodifica a string da url
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT horarios, codigo, observacao FROM linhas WHERE codigo=?", (codigo,))
        linha = cursor.fetchone()
        if linha: #Adicionei essa verificação para evitar erros quando a linha não existe
            horarios = json.loads(linha['horarios']) if linha and linha['horarios'] else {}
            nome_linha = linha['codigo'] if linha else None
            observacao = linha['observacao'] if linha else None
            return render_template("detalhes_horario.html", horarios=horarios, nome_linha=nome_linha, observacao=observacao)
        else:
            return render_template('mensagem_erro.html', mensagem=f"Horários para a linha '{codigo}' não encontrados."), 404
    except sqlite3.Error as e:
        logging.error(f"Erro ao acessar o banco de dados: {e}")
        return render_template('mensagem_erro.html', mensagem="Erro ao acessar o banco de dados. Consulte os logs para mais detalhes."), 500
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar JSON: {e}")
        return render_template('mensagem_erro.html', mensagem="Erro ao processar os horários. Consulte os logs para mais detalhes."), 500
    finally:
        conn.close()
        
@app.route("/raspar")
def raspar():
    try:
        raspagem.main()
        return redirect(url_for('index'))
    except Exception as e:
        return f"Ocorreu um erro durante a raspagem: {e}"

if __name__ == "__main__":
    app.run(debug=True)