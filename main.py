from flask import Flask, redirect, url_for, render_template, request, jsonify, session
from funcs import validar_cpf
import pandas as pd
import socket, sys, os
from datetime import datetime
import json

base_dir = ""

def resource_path(filename: str) -> str:
    """Retorna o caminho absoluto para recursos, útil quando empacotado com PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Caminho do executável em execução (dist/)
        base_dir = os.path.dirname(sys.executable)
    else:
        # Caminho do script (modo desenvolvimento)
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, filename)

# Caminho do arquivo CSV (gravável e acessível)
arquivo = resource_path("data.csv")
arquivo_operadores = resource_path("operadores.json")

app = Flask(__name__,
            template_folder=resource_path("templates"),
            static_folder=resource_path("static"))

# Chave secreta para sessões (IMPORTANTE: mude isso em produção)
app.secret_key = 'festa_servidores_saquarema_2025_secret_key'

# Usuário Master (sempre presente)
USUARIO_MASTER = {
    'usuario': 'master',
    'senha': '0024819',
    'nivel': 'master'
}

def carregar_operadores():
    """Carrega operadores do arquivo JSON"""
    if os.path.exists(arquivo_operadores):
        try:
            with open(arquivo_operadores, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_operadores(operadores):
    """Salva operadores no arquivo JSON"""
    with open(arquivo_operadores, 'w', encoding='utf-8') as f:
        json.dump(operadores, f, ensure_ascii=False, indent=2)

def autenticar(usuario, senha):
    """Autentica usuário (verifica master e operadores)"""
    # Verifica se é o master
    if usuario == USUARIO_MASTER['usuario'] and senha == USUARIO_MASTER['senha']:
        return {'usuario': usuario, 'nivel': 'master'}
    
    # Verifica operadores
    operadores = carregar_operadores()
    if usuario in operadores and operadores[usuario]['senha'] == senha:
        return {'usuario': usuario, 'nivel': 'operador'}
    
    return None

def eh_master():
    """Verifica se o usuário logado é master"""
    return session.get('nivel') == 'master'

@app.route("/", methods=["GET"])
def index():
    if 'operador' not in session:
        return redirect(url_for("login"))
    return redirect(url_for("checkin"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()
        
        auth = autenticar(usuario, senha)
        if auth:
            session['operador'] = auth['usuario']
            session['nivel'] = auth['nivel']
            return redirect(url_for("checkin"))
        else:
            return render_template("login.html", erro="Usu\u00e1rio ou senha inv\u00e1lidos")
    
    return render_template("login.html")

@app.route("/logout", methods=["GET"])
def logout():
    session.pop('operador', None)
    return redirect(url_for("login"))

@app.route("/checkin", methods=["GET"])
def checkin():
    if 'operador' not in session:
        return redirect(url_for("login"))
    return render_template("checkin_form.html", 
                         operador=session.get('operador'),
                         nivel=session.get('nivel'))

@app.route("/buscar", methods=["GET"])
def buscar():
    df = pd.read_csv(arquivo, encoding='utf-8-sig', dtype=str, on_bad_lines='skip')
    df.columns = df.columns.str.lower().str.strip()
    
    # Substituir NaN e valores vazios por string vazia
    df = df.fillna('')
    
    dados = df.to_dict(orient="records")
    query = request.args.get("cpf", "")
    
    print(f"[DEBUG] Buscando CPF: '{query}'")
    print(f"[DEBUG] Total de registros: {len(dados)}")
    if dados:
        print(f"[DEBUG] Primeiro registro CPF: '{dados[0].get('cpf', 'N/A')}'")
    
    resultado = [
        u for u in dados if str(u["cpf"]).startswith(query)
    ]
    
    print(f"[DEBUG] Resultados encontrados: {len(resultado)}")
    
    return jsonify(resultado)

@app.route("/buscar_pulseira", methods=["GET"])
def buscar_pulseira():
    if 'operador' not in session:
        return redirect(url_for("login"))
    return render_template("buscar_pulseira.html", 
                         operador=session.get('operador'),
                         nivel=session.get('nivel'))

@app.route("/buscar_numero", methods=["GET"])
def buscar_numero():
    df = pd.read_csv(arquivo, encoding='utf-8-sig', dtype=str, on_bad_lines='skip')
    df.columns = df.columns.str.lower().str.strip()
    
    # Substituir NaN e valores vazios por string vazia
    df = df.fillna('')
    
    dados = df.to_dict(orient="records")
    query = request.args.get("numeroPulseira", "")
    resultado = [
        u for u in dados if str(u["numeracao"]).startswith(query)
    ]
    return jsonify(resultado)

@app.route("/checkin_validate", methods=["POST"])
def validate():
    if 'operador' not in session:
        return jsonify({"success": False, "error": "Usuário não autenticado"}), 401
    
    try:
        data = request.get_json()
        cpf = str(data.get("cpf"))
        operador = session.get('operador')
        
        print(f"[DEBUG] Operador '{operador}' validando CPF: {cpf}")
        
        df = pd.read_csv(arquivo, encoding='utf-8-sig', dtype=str, on_bad_lines='skip')
        df.columns = df.columns.str.lower().str.strip()
        
        # Substituir NaN por string vazia
        df = df.fillna('')
        
        # Atualiza as colunas validado, validado_por e data_validacao
        print(f"[DEBUG] Registros encontrados antes: {df[df['cpf'] == cpf]['validado'].values}")
        df.loc[df["cpf"] == cpf, "validado"] = "sim"
        df.loc[df["cpf"] == cpf, "validado_por"] = operador
        df.loc[df["cpf"] == cpf, "data_validacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"[DEBUG] Registros encontrados depois: {df[df['cpf'] == cpf]['validado'].values}")
        
        # Tenta salvar o arquivo
        import time
        max_tentativas = 3
        salvou = False
        for tentativa in range(max_tentativas):
            try:
                df.to_csv(arquivo, index=False, encoding='utf-8-sig', mode='w')
                print(f"[DEBUG] Arquivo salvo com sucesso na tentativa {tentativa + 1}")
                salvou = True
                break
            except PermissionError as pe:
                print(f"[DEBUG] Tentativa {tentativa + 1} falhou: PermissionError - {pe}")
                if tentativa < max_tentativas - 1:
                    time.sleep(0.1)
                else:
                    return jsonify({"success": False, "error": "Arquivo está aberto em outro programa. Feche-o e tente novamente."}), 500
        
        # Retorna JSON informando que deu certo
        return jsonify({"success": True, "cpf": cpf, "saved": salvou, "operador": operador})
    except Exception as e:
        print(f"[ERRO] Erro ao validar checkin: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/preencher_campos", methods=["POST"])
def preencher_campos():
    if 'operador' not in session:
        return jsonify({"mensagem": "Usuário não autenticado"}), 401
    
    try:
        dados = request.get_json(force=True)
        operador = session.get('operador')

        print(dados)

        numero = str(dados.get("numero", "")).strip()
        nome = str(dados.get("nome", "")).strip()
        cpf = str(dados.get("cpf", "")).strip()

        if not numero or not nome or not cpf:
            return jsonify({"mensagem": "Todos os campos são obrigatórios."}), 400

        df = pd.read_csv(arquivo, encoding='utf-8-sig', dtype=str, on_bad_lines='skip')
        df.columns = df.columns.str.lower().str.strip()

        mask = df["numeracao"] == numero
        if not mask.any():
            return jsonify({"mensagem": "Número não encontrado no arquivo."}), 404

        df.loc[mask, "nome"] = nome
        df.loc[mask, "cpf"] = cpf
        df.loc[mask, "validado"] = "sim"
        df.loc[mask, "validado_por"] = operador
        df.loc[mask, "data_validacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Tenta salvar o arquivo
        import time
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                df.to_csv(arquivo, index=False, encoding='utf-8-sig', mode='w')
                break
            except PermissionError:
                if tentativa < max_tentativas - 1:
                    time.sleep(0.1)
                else:
                    return jsonify({"mensagem": "Arquivo está aberto em outro programa. Feche-o e tente novamente."}), 500

        return jsonify({"mensagem": f"Dados do número {numero} atualizados com sucesso!"})

    except Exception as e:
        print("Erro ao processar JSON:", e)
        return jsonify({"mensagem": "Erro ao processar requisição."}), 500

@app.route("/gerenciar_operadores", methods=["GET"])
def gerenciar_operadores():
    if 'operador' not in session:
        return redirect(url_for("login"))
    
    if not eh_master():
        return "Acesso negado. Apenas o master pode acessar esta página.", 403
    
    operadores = carregar_operadores()
    mensagem = request.args.get('mensagem', '')
    tipo_mensagem = request.args.get('tipo', '')
    
    return render_template("gerenciar_operadores.html", 
                         operador=session.get('operador'),
                         operadores=operadores,
                         mensagem=mensagem,
                         tipo_mensagem=tipo_mensagem)

@app.route("/adicionar_operador", methods=["POST"])
def adicionar_operador():
    if 'operador' not in session or not eh_master():
        return redirect(url_for("login"))
    
    usuario = request.form.get("usuario", "").strip()
    senha = request.form.get("senha", "").strip()
    
    if not usuario or not senha:
        return redirect(url_for("gerenciar_operadores", mensagem="Usuário e senha são obrigatórios", tipo="erro"))
    
    if usuario == 'master':
        return redirect(url_for("gerenciar_operadores", mensagem="Não é possível criar operador com nome 'master'", tipo="erro"))
    
    operadores = carregar_operadores()
    
    if usuario in operadores:
        return redirect(url_for("gerenciar_operadores", mensagem=f"Operador '{usuario}' já existe", tipo="erro"))
    
    operadores[usuario] = {"senha": senha}
    salvar_operadores(operadores)
    
    return redirect(url_for("gerenciar_operadores", mensagem=f"Operador '{usuario}' adicionado com sucesso!", tipo="sucesso"))

@app.route("/deletar_operador", methods=["POST"])
def deletar_operador():
    if 'operador' not in session or not eh_master():
        return redirect(url_for("login"))
    
    usuario = request.form.get("usuario", "").strip()
    
    operadores = carregar_operadores()
    
    if usuario in operadores:
        del operadores[usuario]
        salvar_operadores(operadores)
        return redirect(url_for("gerenciar_operadores", mensagem=f"Operador '{usuario}' removido com sucesso!", tipo="sucesso"))
    
    return redirect(url_for("gerenciar_operadores", mensagem=f"Operador '{usuario}' não encontrado", tipo="erro"))

@app.route("/editar_operador", methods=["POST"])
def editar_operador():
    if 'operador' not in session or not eh_master():
        return redirect(url_for("login"))
    
    usuario_antigo = request.form.get("usuario_antigo", "").strip()
    usuario_novo = request.form.get("usuario", "").strip()
    senha_nova = request.form.get("senha", "").strip()
    
    if not usuario_novo:
        return redirect(url_for("gerenciar_operadores", mensagem="Nome de usuário é obrigatório", tipo="erro"))
    
    if usuario_novo == 'master':
        return redirect(url_for("gerenciar_operadores", mensagem="Não é possível usar 'master' como nome de usuário", tipo="erro"))
    
    operadores = carregar_operadores()
    
    if usuario_antigo not in operadores:
        return redirect(url_for("gerenciar_operadores", mensagem=f"Operador '{usuario_antigo}' não encontrado", tipo="erro"))
    
    # Se mudou o nome de usuário, verifica se o novo já existe
    if usuario_antigo != usuario_novo and usuario_novo in operadores:
        return redirect(url_for("gerenciar_operadores", mensagem=f"Operador '{usuario_novo}' já existe", tipo="erro"))
    
    # Pega a senha atual
    senha_atual = operadores[usuario_antigo]['senha']
    
    # Remove o operador antigo
    del operadores[usuario_antigo]
    
    # Adiciona com o novo nome e senha (se fornecida nova senha, usa ela; senão mantém a antiga)
    operadores[usuario_novo] = {"senha": senha_nova if senha_nova else senha_atual}
    
    salvar_operadores(operadores)
    
    return redirect(url_for("gerenciar_operadores", mensagem=f"Operador atualizado com sucesso!", tipo="sucesso"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)