import os
import secrets
import sqlite3
from flask import render_template
from functools import wraps
from pathlib import Path

import click
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


BASE_DIR = Path(__file__).resolve().parent
SCHEMA = BASE_DIR / "schema.sql"

app = Flask(__name__, instance_relative_config=True)

INSTANCE_DIR = Path(app.instance_path)
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

app.config["DATABASE"] = (
    INSTANCE_DIR / "equipamentos_clinicos.db"
)

# Usa a variável de ambiente, se configurada.
# Caso contrário, mantém uma chave local persistente.
chave = os.environ.get("SECRET_KEY")

if not chave:
    arquivo_chave = INSTANCE_DIR / "secret_key.txt"

    try:
        with arquivo_chave.open("x", encoding="utf-8") as arquivo:
            arquivo.write(secrets.token_hex(32))
    except FileExistsError:
        pass

    chave = arquivo_chave.read_text(encoding="utf-8").strip()

    if not chave:
        raise RuntimeError(
            "O arquivo instance/secret_key.txt está vazio."
        )

app.config.update(
    SECRET_KEY=chave,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Para publicação com HTTPS, configure como True.
    SESSION_COOKIE_SECURE=False,
)


# ============================================================
# BANCO DE DADOS
# ============================================================

def get_db():
    """Abre uma conexão para o contexto atual."""

    if "db" not in g:
        g.db = sqlite3.connect(
            str(app.config["DATABASE"]),
            timeout=10,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    """
    Executa o schema.sql.

    Execute somente depois de conferir que o arquivo
    não contém comandos destrutivos.
    """

    if not SCHEMA.is_file():
        raise FileNotFoundError(
            f"Arquivo de esquema não encontrado: {SCHEMA}"
        )

    db = get_db()

    with SCHEMA.open("r", encoding="utf-8") as arquivo:
        db.executescript(arquivo.read())

    db.commit()


@app.cli.command("init-db")
def init_db_command():
    """Executa o schema.sql após confirmação."""

    click.confirm(
        "Você conferiu que schema.sql não apaga dados "
        "e deseja executá-lo?",
        abort=True,
    )

    init_db()
    click.echo("Schema executado com sucesso.")


# ============================================================
# CONTAS INICIAIS
# ============================================================

@app.cli.command("criar-contas-iniciais")
def criar_contas_iniciais():
    """Cria contas sem alterar as que já existem."""

    contas = [
        {
            "nome": "Alexandre Silvério Damião dos Santos",
            "email": "alexandre.silverio@treslagoas.ms.gov.br",
            "papel": "administrador_principal",
        },
        {
            "nome": "Marcio Alan Martins",
            "email": "marcio.martins@treslagoas.ms.gov.br",
            "papel": "administrador_principal",
        },
        {
            "nome": "Juliana Rodrigues Salim",
            "email": "juliana.salim@treslagoas.ms.gov.br",
            "papel": "consulta",
        },
    ]

    db = get_db()

    try:
        db.execute(
            """
            SELECT id_usuario, nome, email, senha_hash,
                   papel, ativo, primeiro_acesso
            FROM usuarios
            LIMIT 1
            """
        )
    except sqlite3.Error as erro:
        raise click.ClickException(
            "A tabela usuarios não existe ou não tem os "
            f"campos esperados. Detalhe: {erro}"
        ) from erro

    click.echo("Iniciando o cadastro das contas...")

    for conta in contas:
        existe = db.execute(
            """
            SELECT id_usuario
            FROM usuarios
            WHERE email = ? COLLATE NOCASE
            """,
            (conta["email"],),
        ).fetchone()

        if existe is not None:
            click.echo(
                f"\nConta já existente, mantida: {conta['email']}"
            )
            continue

        click.echo("\n" + "-" * 50)
        click.echo(f"Nome: {conta['nome']}")
        click.echo(f"E-mail: {conta['email']}")
        click.echo(f"Perfil: {conta['papel']}")

        while True:
            senha = click.prompt(
                "Senha temporária com pelo menos 6 caracteres",
                hide_input=True,
                confirmation_prompt="Confirme a senha",
            )

            if len(senha) >= 6:
                break

            click.echo("Use pelo menos 6 caracteres.")

        try:
            db.execute(
                """
                INSERT INTO usuarios (
                    nome,
                    email,
                    senha_hash,
                    papel,
                    ativo,
                    primeiro_acesso
                )
                VALUES (?, ?, ?, ?, 1, 1)
                """,
                (
                    conta["nome"],
                    conta["email"],
                    generate_password_hash(senha),
                    conta["papel"],
                ),
            )
            db.commit()

        except sqlite3.Error as erro:
            db.rollback()

            raise click.ClickException(
                f"Não foi possível criar {conta['email']}: {erro}"
            ) from erro

        click.echo("Conta criada com sucesso.")

    click.echo("\nCadastro inicial concluído.")


# ============================================================
# SESSÃO, USUÁRIO E PROTEÇÃO DOS FORMULÁRIOS
# ============================================================

@app.before_request
def carregar_usuario_logado():
    g.usuario = None

    id_usuario = session.get("id_usuario")

    if id_usuario is not None:
        g.usuario = get_db().execute(
            """
            SELECT id_usuario, nome, email, papel,
                   ativo, primeiro_acesso
            FROM usuarios
            WHERE id_usuario = ?
              AND ativo = 1
            """,
            (id_usuario,),
        ).fetchone()

        if g.usuario is None:
            session.clear()

    # Confere o token em todas as requisições POST.
    if request.method == "POST":
        esperado = session.get("_csrf_token")
        recebido = request.form.get("_csrf_token", "")

        if (
            not esperado
            or not secrets.compare_digest(esperado, recebido)
        ):
            abort(
                400,
                description=(
                    "Formulário expirado ou inválido. "
                    "Recarregue a página e tente novamente."
                ),
            )


def csrf_token():
    token = session.get("_csrf_token")

    if token is None:
        token = secrets.token_hex(32)
        session["_csrf_token"] = token

    return token


app.jinja_env.globals["csrf_token"] = csrf_token


def login_obrigatorio(funcao):
    @wraps(funcao)
    def verificar(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("login"))

        if g.usuario["primeiro_acesso"]:
            return redirect(url_for("trocar_senha"))

        return funcao(*args, **kwargs)

    return verificar


# ============================================================
# TELAS BÁSICAS INDEPENDENTES DOS TEMPLATES EXISTENTES
# ============================================================

ESTILO = """
<style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: #f1f5f9;
        color: #1e293b;
    }
    header {
        padding: 20px;
        color: white;
        background: #0f4565;
    }
    header h1 { margin: 0; font-size: 22px; }
    main {
        max-width: 680px;
        margin: 35px auto;
        padding: 25px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 3px 16px #00000012;
    }
    label {
        display: block;
        margin-top: 18px;
        font-weight: bold;
    }
    input {
        width: 100%;
        padding: 12px;
        margin-top: 6px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        font-size: 16px;
    }
    button {
        margin-top: 22px;
        padding: 12px 20px;
        border: 0;
        border-radius: 6px;
        color: white;
        background: #0f4565;
        cursor: pointer;
        font-size: 16px;
    }
    .mensagem {
        padding: 12px;
        margin-bottom: 15px;
        border-radius: 6px;
        background: #e0f2fe;
    }
    .erro { background: #fee2e2; color: #991b1b; }
    .sucesso { background: #dcfce7; color: #166534; }
    dt { margin-top: 16px; font-weight: bold; }
    dd { margin: 5px 0 0; overflow-wrap: anywhere; }
    @media (max-width: 720px) {
        main { margin: 20px 12px; }
    }
</style>
"""

INICIO_HTML = (
    """
<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">
    <title>{{ titulo }} — Gestão de Equipamentos Clínicos</title>
"""
    + ESTILO
    + """
</head>
<body>
<header>
    <h1>Gestão de Equipamentos Clínicos</h1>
</header>
<main>
    {% for categoria, mensagem in
       get_flashed_messages(with_categories=true) %}
        <div class="mensagem {{ categoria }}" role="alert">
            {{ mensagem }}
        </div>
    {% endfor %}
"""
)

FIM_HTML = """
</main>
</body>
</html>
"""

LOGIN_HTML = INICIO_HTML + """
<h2>Entrar no sistema</h2>

<form method="post" action="{{ url_for('login') }}">
    <input type="hidden" name="_csrf_token"
           value="{{ csrf_token() }}">

    <label for="email">E-mail</label>
    <input id="email" name="email" type="email"
           value="{{ email }}"
           autocomplete="username" required>

    <label for="senha">Senha</label>
    <input id="senha" name="senha" type="password"
           autocomplete="current-password" required>

    <button type="submit">Entrar</button>
</form>
""" + FIM_HTML

TROCAR_SENHA_HTML = INICIO_HTML + """
<h2>Definir nova senha</h2>

<p>
    {{ g.usuario["nome"] }}, antes de acessar o painel,
    substitua sua senha temporária.
</p>

<form method="post" action="{{ url_for('trocar_senha') }}">
    <input type="hidden" name="_csrf_token"
           value="{{ csrf_token() }}">

    <label for="senha_atual">Senha temporária atual</label>
    <input id="senha_atual" name="senha_atual"
           type="password"
           autocomplete="current-password" required>

    <label for="nova_senha">Nova senha</label>
    <input id="nova_senha" name="nova_senha"
           type="password" minlength="6"
           autocomplete="new-password" required>

    <label for="confirmacao">Confirme a nova senha</label>
    <input id="confirmacao" name="confirmacao"
           type="password" minlength="6"
           autocomplete="new-password" required>

    <button type="submit">Salvar nova senha</button>
</form>

<form method="post" action="{{ url_for('logout') }}">
    <input type="hidden" name="_csrf_token"
           value="{{ csrf_token() }}">
    <button type="submit">Sair</button>
</form>
""" + FIM_HTML

PAINEL_HTML = INICIO_HTML + """
<h2>Painel inicial</h2>

<p>Bem-vindo(a), {{ g.usuario["nome"] }}.</p>

<dl>
    <dt>E-mail</dt>
    <dd>{{ g.usuario["email"] }}</dd>

    <dt>Perfil</dt>
    <dd>{{ g.usuario["papel"] }}</dd>
</dl>

<p>
    O acesso à conta está funcionando.
    As telas de equipamentos ainda precisam ser integradas.
</p>

<form method="post" action="{{ url_for('logout') }}">
    <input type="hidden" name="_csrf_token"
           value="{{ csrf_token() }}">
    <button type="submit">Sair do sistema</button>
</form>
""" + FIM_HTML


# ============================================================
# ROTAS
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        if g.usuario["primeiro_acesso"]:
            return redirect(url_for("trocar_senha"))

        return redirect(url_for("painel"))

    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        usuario = get_db().execute(
            """
            SELECT *
            FROM usuarios
            WHERE email = ? COLLATE NOCASE
              AND ativo = 1
            """,
            (email,),
        ).fetchone()

        if (
            usuario is None
            or not check_password_hash(
                usuario["senha_hash"], senha
            )
        ):
            flash("E-mail ou senha inválidos.", "erro")

        else:
            session.clear()
            session["id_usuario"] = usuario["id_usuario"]

            if usuario["primeiro_acesso"]:
                return redirect(url_for("trocar_senha"))

            return redirect(url_for("painel"))

    return render_template("login.html")


@app.route("/trocar-senha", methods=["GET", "POST"])
def trocar_senha():
    if g.usuario is None:
        return redirect(url_for("login"))

    if not g.usuario["primeiro_acesso"]:
        return redirect(url_for("painel"))

    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmacao = request.form.get("confirmacao", "")

        db = get_db()

        usuario = db.execute(
            """
            SELECT senha_hash
            FROM usuarios
            WHERE id_usuario = ?
            """,
            (g.usuario["id_usuario"],),
        ).fetchone()

        erro = None

        if not check_password_hash(
            usuario["senha_hash"], senha_atual
        ):
            erro = "A senha temporária atual está incorreta."

        elif len(nova_senha) < 6:
            erro = "A nova senha deve ter pelo menos 6 caracteres."

        elif nova_senha != confirmacao:
            erro = "A confirmação não coincide com a nova senha."

        elif check_password_hash(
            usuario["senha_hash"], nova_senha
        ):
            erro = "Escolha uma senha diferente da temporária."

        if erro:
            flash(erro, "erro")

        else:
            try:
                db.execute(
                    """
                    UPDATE usuarios
                    SET senha_hash = ?,
                        primeiro_acesso = 0
                    WHERE id_usuario = ?
                    """,
                    (
                        generate_password_hash(nova_senha),
                        g.usuario["id_usuario"],
                    ),
                )
                db.commit()

            except sqlite3.Error:
                db.rollback()
                app.logger.exception("Erro ao atualizar senha")
                flash(
                    "Não foi possível salvar a senha. "
                    "Tente novamente.",
                    "erro",
                )

            else:
                id_usuario = g.usuario["id_usuario"]
                session.clear()
                session["id_usuario"] = id_usuario

                flash(
                    "Senha atualizada com sucesso.",
                    "sucesso",
                )

                return redirect(url_for("painel"))

    return render_template_string(
        TROCAR_SENHA_HTML,
        titulo="Trocar senha",
    )


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_obrigatorio
def painel():
    db = get_db()

    unidades = db.execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(
                SUM(
                    CASE
                        WHEN ativo = 1 THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS ativas
        FROM unidades
        """
    ).fetchone()

    equipamentos = db.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM equipamentos) AS total,
            (
                SELECT COUNT(*)
                FROM equipamentos e
                WHERE e.situacao = 'Em manutenção'
                    OR EXISTS (
                        SELECT 1
                        FROM ordens_servico o
                        WHERE o.id_equipamento = e.id_equipamento
                            AND o.situacao = 'Em andamento'
                    )
            ) AS em_manutencao
        """
    ).fetchone()


from unidades import registrar_unidades
from equipamentos import registrar_equipamentos
from ordens_servico import registrar_ordens_servico


registrar_unidades(
    app,
    get_db,
    login_obrigatorio,
)

registrar_equipamentos(
    app,
    get_db,
    login_obrigatorio,
)

registrar_ordens_servico(
    app,
    get_db,
    login_obrigatorio,
)


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )
