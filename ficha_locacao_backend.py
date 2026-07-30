"""
Módulo de Ficha Cadastral de Locação
=====================================

COMO INTEGRAR NA SUA API FLASK EXISTENTE (PythonAnywhere):

1. Copie este arquivo para a mesma pasta do seu app Flask principal
   (a pasta que contém o arquivo que o PythonAnywhere aponta como "WSGI").

2. No seu arquivo principal (ex: app.py, flask_app.py), adicione:

       from ficha_locacao_backend import ficha_locacao_bp
       app.register_blueprint(ficha_locacao_bp)

3. Ajuste as constantes abaixo (UPLOAD_FOLDER e DB_PATH) para caminhos
   reais dentro da sua conta do PythonAnywhere. Exemplo típico:

       UPLOAD_FOLDER = "/home/antoniofurtado/mysite/uploads/fichas_locacao"
       DB_PATH = "/home/antoniofurtado/mysite/fichas_locacao.db"

4. Na aba "Web" do PythonAnywhere, adicione uma pasta estática (ou apenas
   confie no fato de que o Flask já serve arquivos): não é necessário
   mapear a pasta de uploads como estática, pois os documentos NÃO devem
   ser acessíveis publicamente (são dados sensíveis).

5. Clique em "Reload" na aba Web do PythonAnywhere para aplicar.

IMPORTANTE SOBRE LIMITAÇÕES DO PLANO GRATUITO:
- O plano gratuito do PythonAnywhere tem cota de armazenamento em disco
  limitada (histórico: em torno de 512MB). Cada ficha com 3 documentos
  pode ocupar alguns MB. Monitore o uso de disco periodicamente.
- Se a conta "dormir" (necessidade de reativação mensal mencionada no seu
  fluxo atual), o formulário no site vai falhar ao enviar até você
  reativar. Isso já está tratado com uma mensagem amigável no frontend.
"""

import os
import sqlite3
import re
import uuid
import secrets
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, send_from_directory

ficha_locacao_bp = Blueprint('ficha_locacao', __name__)

# ============================================================
# CONFIGURAÇÃO — AJUSTE ESTES CAMINHOS PARA O SEU AMBIENTE
# ============================================================
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "fichas_locacao")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichas_locacao.db")

EXTENSOES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.pdf'}
TAMANHO_MAXIMO_ARQUIVO = 10 * 1024 * 1024  # 10MB por arquivo

CAMPOS_TEXTO_OBRIGATORIOS = [
    'nome_completo', 'data_nascimento', 'estado_civil', 'nacionalidade',
    'cpf', 'rg_orgao_expedidor', 'renda_mensal_bruta',
    'telefone_celular', 'email_principal', 'endereco_residencial',
]
CAMPOS_TEXTO_OPCIONAIS = [
    'profissao', 'cep', 'cidade_estado', 'tempo_moradia', 'possui_comprovante_renda',
]
CAMPOS_ARQUIVO_OBRIGATORIOS = [
    'doc_identificacao', 'comprovante_renda', 'comprovante_residencia',
]

# ============================================================
# AUTENTICAÇÃO DOS ENDPOINTS ADMINISTRATIVOS
# ============================================================
# As credenciais vêm de variáveis de ambiente, para você NÃO precisar
# deixar usuário/senha escritos direto no código.
#
# Como configurar no PythonAnywhere:
#   1. Aba "Web" > seção "Environment variables" (perto do fim da página).
#   2. Adicione:
#        FICHA_LOCACAO_ADMIN_USER = escolha um usuário
#        FICHA_LOCACAO_ADMIN_PASS = escolha uma senha forte
#   3. Clique em "Reload" na aba Web.
#
# Se você não configurar essas variáveis, o sistema usa o valor padrão
# abaixo ("admin" / "TROQUE_ESTA_SENHA") — o que É INSEGURO. Troque
# antes de publicar, mesmo que seja rapidamente pelas variáveis de
# ambiente.
ADMIN_USUARIO = os.environ.get("FICHA_LOCACAO_ADMIN_USER", "admin")
ADMIN_SENHA = os.environ.get("FICHA_LOCACAO_ADMIN_PASS", "TROQUE_ESTA_SENHA")


def requer_autenticacao(funcao):
    """Decorador que exige HTTP Basic Auth válido antes de executar a rota."""
    @wraps(funcao)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        usuario_ok = auth and secrets.compare_digest(auth.username or '', ADMIN_USUARIO)
        senha_ok = auth and secrets.compare_digest(auth.password or '', ADMIN_SENHA)
        if not (usuario_ok and senha_ok):
            return jsonify({"sucesso": False, "erro": "Não autorizado"}), 401, {
                'WWW-Authenticate': 'Basic realm="Área administrativa - Fichas de Locação"'
            }
        return funcao(*args, **kwargs)
    return wrapper


def _init_db():
    """Cria a tabela de fichas de locação se ainda não existir."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fichas_locacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT UNIQUE,
            data_envio TEXT,
            nome_completo TEXT,
            data_nascimento TEXT,
            estado_civil TEXT,
            nacionalidade TEXT,
            cpf TEXT,
            rg_orgao_expedidor TEXT,
            profissao TEXT,
            renda_mensal_bruta TEXT,
            telefone_celular TEXT,
            email_principal TEXT,
            endereco_residencial TEXT,
            cep TEXT,
            cidade_estado TEXT,
            tempo_moradia TEXT,
            possui_comprovante_renda TEXT,
            arquivo_doc_identificacao TEXT,
            arquivo_comprovante_renda TEXT,
            arquivo_comprovante_residencia TEXT,
            status TEXT DEFAULT 'novo'
        )
    """)
    conn.commit()
    conn.close()


def _extensao_valida(nome_arquivo):
    _, ext = os.path.splitext(nome_arquivo.lower())
    return ext in EXTENSOES_PERMITIDAS


def _somente_digitos(texto):
    return re.sub(r'\D', '', texto or '')


@ficha_locacao_bp.route('/api/ficha-locacao', methods=['POST'])
def receber_ficha_locacao():
    _init_db()

    erros = []

    # --- Validação dos campos de texto obrigatórios ---
    dados = {}
    for campo in CAMPOS_TEXTO_OBRIGATORIOS:
        valor = request.form.get(campo, '').strip()
        if not valor:
            erros.append(f"Campo obrigatório ausente: {campo}")
        dados[campo] = valor

    for campo in CAMPOS_TEXTO_OPCIONAIS:
        dados[campo] = request.form.get(campo, '').strip()

    # --- Validação de e-mail simples ---
    email = dados.get('email_principal', '')
    if email and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        erros.append("E-mail principal inválido")

    # --- Validação de CPF (11 dígitos) ---
    cpf_digitos = _somente_digitos(dados.get('cpf', ''))
    if len(cpf_digitos) != 11:
        erros.append("CPF deve conter 11 dígitos")

    # --- Validação dos arquivos obrigatórios ---
    arquivos_recebidos = {}
    for campo in CAMPOS_ARQUIVO_OBRIGATORIOS:
        arquivo = request.files.get(campo)
        if not arquivo or arquivo.filename == '':
            erros.append(f"Arquivo obrigatório ausente: {campo}")
            continue
        if not _extensao_valida(arquivo.filename):
            erros.append(f"Formato de arquivo não permitido em {campo} (use JPG, PNG ou PDF)")
            continue
        arquivo.seek(0, os.SEEK_END)
        tamanho = arquivo.tell()
        arquivo.seek(0)
        if tamanho > TAMANHO_MAXIMO_ARQUIVO:
            erros.append(f"Arquivo em {campo} excede o limite de 10MB")
            continue
        arquivos_recebidos[campo] = arquivo

    if erros:
        return jsonify({"sucesso": False, "erros": erros}), 400

    # --- Geração de protocolo único e pasta de destino ---
    protocolo = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
    pasta_ficha = os.path.join(UPLOAD_FOLDER, protocolo)
    os.makedirs(pasta_ficha, exist_ok=True)

    caminhos_salvos = {}
    try:
        for campo, arquivo in arquivos_recebidos.items():
            nome_seguro = secure_filename(arquivo.filename)
            nome_final = f"{campo}_{nome_seguro}"
            destino = os.path.join(pasta_ficha, nome_final)
            arquivo.save(destino)
            caminhos_salvos[campo] = os.path.join(protocolo, nome_final)
    except Exception as e:
        return jsonify({"sucesso": False, "erros": [f"Erro ao salvar arquivos: {str(e)}"]}), 500

    # --- Gravação no banco ---
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO fichas_locacao (
                protocolo, data_envio, nome_completo, data_nascimento, estado_civil,
                nacionalidade, cpf, rg_orgao_expedidor, profissao, renda_mensal_bruta,
                telefone_celular, email_principal, endereco_residencial, cep,
                cidade_estado, tempo_moradia, possui_comprovante_renda,
                arquivo_doc_identificacao, arquivo_comprovante_renda, arquivo_comprovante_residencia,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            protocolo, datetime.now().isoformat(), dados['nome_completo'], dados['data_nascimento'],
            dados['estado_civil'], dados['nacionalidade'], cpf_digitos, dados['rg_orgao_expedidor'],
            dados.get('profissao', ''), dados['renda_mensal_bruta'], dados['telefone_celular'],
            dados['email_principal'], dados['endereco_residencial'], dados.get('cep', ''),
            dados.get('cidade_estado', ''), dados.get('tempo_moradia', ''),
            dados.get('possui_comprovante_renda', ''),
            caminhos_salvos.get('doc_identificacao', ''),
            caminhos_salvos.get('comprovante_renda', ''),
            caminhos_salvos.get('comprovante_residencia', ''),
            'novo'
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"sucesso": False, "erros": [f"Erro ao gravar no banco: {str(e)}"]}), 500

    return jsonify({"sucesso": True, "protocolo": protocolo}), 200


# ============================================================
# ENDPOINTS DE CONSULTA (uso interno / administrativo)
# ============================================================
# Protegidos por HTTP Basic Auth (ver ADMIN_USUARIO/ADMIN_SENHA acima).
# No navegador, ao acessar a URL diretamente, ele vai pedir usuário e
# senha automaticamente. Em código (ex: seu app PyQt6), envie o header
# Authorization: Basic <usuario:senha em base64>.

@ficha_locacao_bp.route('/api/fichas-locacao', methods=['GET'])
@requer_autenticacao
def listar_fichas_locacao():
    """Lista todas as fichas recebidas (sem os arquivos, só os metadados)."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    linhas = conn.execute(
        "SELECT id, protocolo, data_envio, nome_completo, cpf, telefone_celular, "
        "email_principal, renda_mensal_bruta, status FROM fichas_locacao ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify({"fichas": [dict(l) for l in linhas]}), 200


@ficha_locacao_bp.route('/api/fichas-locacao/<protocolo>', methods=['GET'])
@requer_autenticacao
def detalhe_ficha_locacao(protocolo):
    """Retorna todos os dados de uma ficha específica pelo protocolo."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    linha = conn.execute(
        "SELECT * FROM fichas_locacao WHERE protocolo = ?", (protocolo,)
    ).fetchone()
    conn.close()
    if not linha:
        return jsonify({"sucesso": False, "erro": "Ficha não encontrada"}), 404
    return jsonify(dict(linha)), 200


@ficha_locacao_bp.route('/api/fichas-locacao/<protocolo>/arquivo/<campo>', methods=['GET'])
@requer_autenticacao
def baixar_arquivo_ficha(protocolo, campo):
    """Baixa um documento específico de uma ficha (RG, comprovante de renda ou residência)."""
    if campo not in CAMPOS_ARQUIVO_OBRIGATORIOS:
        return jsonify({"sucesso": False, "erro": "Campo de arquivo inválido"}), 400

    # protocolo é gerado internamente por nós (timestamp + hex), então
    # validamos o formato para impedir tentativa de path traversal
    if not re.match(r'^[0-9a-zA-Z\-]+$', protocolo):
        return jsonify({"sucesso": False, "erro": "Protocolo inválido"}), 400

    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    linha = conn.execute(
        f"SELECT arquivo_{campo} AS caminho FROM fichas_locacao WHERE protocolo = ?", (protocolo,)
    ).fetchone()
    conn.close()

    if not linha or not linha['caminho']:
        return jsonify({"sucesso": False, "erro": "Arquivo não encontrado"}), 404

    caminho_relativo = linha['caminho']  # ex: "20260729-abcd1234/comprovante_renda_holerite.pdf"
    pasta, nome_arquivo = os.path.split(caminho_relativo)
    pasta_completa = os.path.join(UPLOAD_FOLDER, pasta)

    # ?inline=1 permite exibir a imagem/PDF direto no navegador (usado pelo
    # painel administrativo abaixo); sem o parâmetro, força o download
    # (comportamento original, mantido para não quebrar integrações existentes).
    modo_inline = request.args.get('inline') == '1'
    return send_from_directory(pasta_completa, nome_arquivo, as_attachment=not modo_inline)


# ============================================================
# PAINEL ADMINISTRATIVO (visualização simples em HTML)
# ============================================================
# Protegido pela mesma autenticação básica dos endpoints acima.
# Pensado para uso humano direto no navegador: lista as fichas recebidas
# e, ao abrir uma delas, mostra todos os dados junto com os documentos
# anexados (imagens aparecem na tela, PDFs abrem em nova aba).

_PAINEL_ESTILO = """
<style>
    * { box-sizing: border-box; }
    body {
        font-family: 'Lato', 'Segoe UI', Arial, sans-serif;
        background: #f8f8f8;
        color: #1a1a1a;
        margin: 0;
        padding: 0;
    }
    header.painel-topo {
        background: #1a1a1a;
        padding: 20px 32px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    header.painel-topo h1 {
        color: #D4AF37;
        font-size: 20px;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.5px;
    }
    header.painel-topo a {
        color: #f8f8f8;
        text-decoration: none;
        font-size: 14px;
        border: 1px solid rgba(255,255,255,0.3);
        padding: 6px 14px;
        border-radius: 4px;
    }
    header.painel-topo a:hover { border-color: #D4AF37; color: #D4AF37; }
    .painel-container { max-width: 1100px; margin: 0 auto; padding: 28px 24px 80px; }
    table.painel-tabela { width: 100%; border-collapse: collapse; background: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    table.painel-tabela th {
        background: #1a1a1a; color: #D4AF37; text-align: left;
        padding: 12px 14px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;
    }
    table.painel-tabela td { padding: 12px 14px; font-size: 14.5px; border-top: 1px solid #eee; }
    table.painel-tabela tr:hover td { background: #fffdf5; }
    table.painel-tabela a.painel-link-linha { color: #1a1a1a; text-decoration: none; font-weight: 600; }
    table.painel-tabela a.painel-link-linha:hover { color: #2e7d6e; }
    .painel-vazio { padding: 40px; text-align: center; color: #777; background: white; border-radius: 6px; }
    .painel-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .painel-badge.novo { background: #fff3cd; color: #8a6d00; }
    .painel-badge.aprovado { background: #e6f7e6; color: #2e7d32; }
    .painel-badge.reprovado { background: #fdecea; color: #c0392b; }
    .painel-badge.outro { background: #eee; color: #555; }
    .painel-card { background: white; border-radius: 6px; padding: 26px 30px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    .painel-card h3 { font-size: 17px; color: #2e7d6e; border-bottom: 2px solid #D4AF37; padding-bottom: 10px; margin: 0 0 16px; }
    .painel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px 24px; }
    .painel-campo label { display: block; font-size: 12px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3px; }
    .painel-campo div { font-size: 15px; color: #1a1a1a; }
    .painel-doc { border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; text-align: center; }
    .painel-doc img { max-width: 100%; max-height: 320px; border-radius: 4px; display: block; margin: 0 auto 10px; }
    .painel-doc .painel-doc-titulo { font-size: 13.5px; font-weight: 700; color: #555; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
    .painel-doc a.painel-abrir { display: inline-block; margin-top: 4px; background: #1a1a1a; color: white; padding: 9px 18px; border-radius: 4px; font-size: 13.5px; text-decoration: none; }
    .painel-doc a.painel-abrir:hover { background: #D4AF37; color: #1a1a1a; }
    .painel-voltar { display: inline-block; margin-bottom: 16px; color: #555; text-decoration: none; font-size: 14px; }
    .painel-voltar:hover { color: #2e7d6e; }
</style>
"""


def _badge_status(status):
    status = (status or 'novo').lower()
    classe = {
        'novo': 'novo',
        'aprovado': 'aprovado',
        'reprovado': 'reprovado',
    }.get(status, 'outro')
    return f'<span class="painel-badge {classe}">{status}</span>'


@ficha_locacao_bp.route('/admin/fichas-locacao', methods=['GET'])
@requer_autenticacao
def painel_fichas_locacao():
    """Painel simples em HTML com a lista de fichas recebidas."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    linhas = conn.execute(
        "SELECT protocolo, data_envio, nome_completo, cpf, telefone_celular, "
        "email_principal, renda_mensal_bruta, status FROM fichas_locacao ORDER BY id DESC"
    ).fetchall()
    conn.close()

    linhas_html = ""
    for l in linhas:
        cpf_fmt = l['cpf']
        if cpf_fmt and len(cpf_fmt) == 11:
            cpf_fmt = f"{cpf_fmt[:3]}.{cpf_fmt[3:6]}.{cpf_fmt[6:9]}-{cpf_fmt[9:]}"
        data_fmt = (l['data_envio'] or '')[:16].replace('T', ' ')
        linhas_html += f"""
        <tr>
            <td><a class="painel-link-linha" href="/admin/fichas-locacao/{l['protocolo']}">{l['nome_completo']}</a></td>
            <td>{cpf_fmt or '—'}</td>
            <td>{l['telefone_celular'] or '—'}</td>
            <td>{l['renda_mensal_bruta'] or '—'}</td>
            <td>{data_fmt}</td>
            <td>{_badge_status(l['status'])}</td>
        </tr>
        """

    corpo = f"""
    <div class="painel-vazio">Nenhuma ficha recebida até o momento.</div>
    """ if not linhas else f"""
    <table class="painel-tabela">
        <thead>
            <tr><th>Nome</th><th>CPF</th><th>Telefone</th><th>Renda</th><th>Recebido em</th><th>Status</th></tr>
        </thead>
        <tbody>
            {linhas_html}
        </tbody>
    </table>
    """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fichas de Locação Recebidas</title>
    <meta name="robots" content="noindex, nofollow">
    {_PAINEL_ESTILO}
</head>
<body>
    <header class="painel-topo">
        <h1>📋 Fichas Cadastrais de Locação</h1>
    </header>
    <div class="painel-container">
        {corpo}
    </div>
</body>
</html>"""
    return html, 200


@ficha_locacao_bp.route('/admin/fichas-locacao/<protocolo>', methods=['GET'])
@requer_autenticacao
def painel_detalhe_ficha_locacao(protocolo):
    """Painel simples em HTML com todos os dados e documentos de uma ficha."""
    if not re.match(r'^[0-9a-zA-Z\-]+$', protocolo):
        return "Protocolo inválido", 400

    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    linha = conn.execute(
        "SELECT * FROM fichas_locacao WHERE protocolo = ?", (protocolo,)
    ).fetchone()
    conn.close()

    if not linha:
        return "Ficha não encontrada", 404

    dados = dict(linha)
    cpf_fmt = dados.get('cpf', '')
    if cpf_fmt and len(cpf_fmt) == 11:
        cpf_fmt = f"{cpf_fmt[:3]}.{cpf_fmt[3:6]}.{cpf_fmt[6:9]}-{cpf_fmt[9:]}"

    def campo(rotulo, valor):
        return f"""
        <div class="painel-campo">
            <label>{rotulo}</label>
            <div>{valor or '—'}</div>
        </div>
        """

    campos_html = (
        campo("Nome Completo", dados.get('nome_completo'))
        + campo("Data de Nascimento", dados.get('data_nascimento'))
        + campo("Estado Civil", dados.get('estado_civil'))
        + campo("Nacionalidade", dados.get('nacionalidade'))
        + campo("CPF", cpf_fmt)
        + campo("RG / Órgão Expedidor", dados.get('rg_orgao_expedidor'))
        + campo("Profissão", dados.get('profissao'))
        + campo("Renda Mensal Bruta", dados.get('renda_mensal_bruta'))
        + campo("Telefone Celular", dados.get('telefone_celular'))
        + campo("E-mail Principal", dados.get('email_principal'))
        + campo("Endereço Residencial", dados.get('endereco_residencial'))
        + campo("CEP", dados.get('cep'))
        + campo("Cidade e Estado", dados.get('cidade_estado'))
        + campo("Tempo de Moradia", dados.get('tempo_moradia'))
        + campo("Possui Comprovante de Renda", dados.get('possui_comprovante_renda'))
        + campo("Status", _badge_status(dados.get('status')))
    )

    docs_config = [
        ("doc_identificacao", "Documento de Identificação"),
        ("comprovante_renda", "Comprovante de Renda"),
        ("comprovante_residencia", "Comprovante de Residência"),
    ]

    docs_html = ""
    for campo_arquivo, titulo in docs_config:
        caminho = dados.get(f"arquivo_{campo_arquivo}")
        if not caminho:
            docs_html += f"""
            <div class="painel-doc">
                <div class="painel-doc-titulo">{titulo}</div>
                <div style="color:#999; font-size: 13.5px;">Não enviado</div>
            </div>
            """
            continue

        _, ext = os.path.splitext(caminho.lower())
        url_inline = f"/api/fichas-locacao/{protocolo}/arquivo/{campo_arquivo}?inline=1"
        url_download = f"/api/fichas-locacao/{protocolo}/arquivo/{campo_arquivo}"

        if ext in ('.jpg', '.jpeg', '.png'):
            docs_html += f"""
            <div class="painel-doc">
                <div class="painel-doc-titulo">{titulo}</div>
                <a href="{url_inline}" target="_blank">
                    <img src="{url_inline}" alt="{titulo}">
                </a>
                <div><a class="painel-abrir" href="{url_download}">⬇ Baixar</a></div>
            </div>
            """
        else:
            docs_html += f"""
            <div class="painel-doc">
                <div class="painel-doc-titulo">{titulo}</div>
                <div style="font-size: 40px; margin: 10px 0;">📄</div>
                <a class="painel-abrir" href="{url_inline}" target="_blank">Abrir PDF</a>
            </div>
            """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ficha de {dados.get('nome_completo', '')} | Fichas de Locação</title>
    <meta name="robots" content="noindex, nofollow">
    {_PAINEL_ESTILO}
</head>
<body>
    <header class="painel-topo">
        <h1>📋 Ficha Cadastral de Locação</h1>
        <a href="/admin/fichas-locacao">← Voltar à lista</a>
    </header>
    <div class="painel-container">
        <a class="painel-voltar" href="/admin/fichas-locacao">← Voltar à lista de fichas</a>

        <div class="painel-card">
            <h3>Dados do Proponente</h3>
            <div class="painel-grid">
                {campos_html}
            </div>
        </div>

        <div class="painel-card">
            <h3>Documentos Anexados</h3>
            <div class="painel-grid">
                {docs_html}
            </div>
        </div>
    </div>
</body>
</html>"""
    return html, 200
