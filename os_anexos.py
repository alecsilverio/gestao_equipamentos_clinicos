import re
import sqlite3
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import (
    abort,
    flash,
    g,
    redirect,
    render_template_string,
    request,
    send_file,
    url_for,
)
from pypdf import PdfReader
from werkzeug.utils import secure_filename


LIMITE_PDF_BYTES = 10 * 1024 * 1024
LIMITE_REQUISICAO_BYTES = 12 * 1024 * 1024

PADRAO_NOME_INTERNO = re.compile(r"^[0-9a-f]{32}\.pdf$")


PAGINA_ANEXOS_HTML = """
{% extends "base.html" %}

{% block title %}
    Documentos da OS {{ ordem["numero_os"] or ordem["id_os"] }}
    | Gestão de Equipamentos Clínicos
{% endblock %}

{% block extra_head %}
<style>
    .anexo-acoes {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 12px;
        margin: 18px 0;
    }

    .anexo-botao {
        display: inline-block;
        padding: 10px 16px;
        border: 0;
        border-radius: 6px;
        background: #0f4565;
        color: white;
        text-decoration: none;
        cursor: pointer;
        font: inherit;
    }

    .anexo-botao--secundario {
        background: #475569;
    }

    .anexo-campo label {
        display: block;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .anexo-campo input {
        max-width: 100%;
        padding: 10px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        font: inherit;
    }

    .anexo-campo small {
        display: block;
        margin-top: 8px;
        color: #475569;
    }

    .anexo-ajuda {
        padding: 16px;
        margin: 18px 0;
        border-radius: 6px;
        background: #e0f2fe;
        color: #0c4a6e;
    }

    .anexo-erro {
        padding: 16px;
        margin: 18px 0;
        border-radius: 6px;
        background: #fee2e2;
        color: #991b1b;
    }

    .anexo-tabela-container {
        overflow-x: auto;
    }

    .anexo-tabela {
        width: 100%;
        border-collapse: collapse;
    }

    .anexo-tabela th,
    .anexo-tabela td {
        padding: 12px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
        vertical-align: top;
    }

    .anexo-tabela th {
        background: #f1f5f9;
    }

    .anexo-tabela td {
        overflow-wrap: anywhere;
    }
</style>
{% endblock %}

{% block content %}
<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">
            DOCUMENTOS DA ORDEM DE SERVIÇO
        </p>

        <h1>
            OS {{ ordem["numero_os"] or ("sem número — ID " ~ ordem["id_os"]) }}
        </h1>

        <p class="descricao">
            Unidade do atendimento:
            {{ ordem["unidade_nome"] }}
        </p>

        <p>
            Equipamento:
            {% if ordem["id_equipamento"] is not none %}
                {{ ordem["equipamento_nome"] }}
                — Patrimônio:
                {{ ordem["equipamento_patrimonio"] or "Não informado" }}
            {% else %}
                {{ ordem["descricao_equipamento"] or "Ainda não vinculado" }}
            {% endif %}
        </p>

        <p>
            Situação da OS: {{ ordem["situacao"] }}
        </p>
    </div>
</section>

<div class="anexo-acoes">
    <a class="anexo-botao anexo-botao--secundario"
       href="{{ url_for('ordens_lista') }}">
        Voltar às ordens de serviço
    </a>

    <a class="anexo-botao"
       href="{{ url_for('ordens_editar', id_os=ordem['id_os']) }}">
        {{ "Editar OS" if administrador else "Visualizar OS" }}
    </a>
</div>

{% if erro %}
    <div class="anexo-erro" role="alert">
        {{ erro }}
    </div>
{% endif %}

{% if administrador %}
    <section class="painel">
        <h2>Anexar documento PDF</h2>

        <p>
            Confira se o documento pertence a esta OS
            antes de enviá-lo.
        </p>

        <form
            method="post"
            action="{{ url_for('ordens_anexos', id_os=ordem['id_os']) }}"
            enctype="multipart/form-data"
        >
            <input
                type="hidden"
                name="_csrf_token"
                value="{{ csrf_token() }}"
            >

            <div class="anexo-campo">
                <label for="arquivo">
                    Arquivo PDF *
                </label>

                <input
                    id="arquivo"
                    name="arquivo"
                    type="file"
                    accept=".pdf,application/pdf"
                    required
                >

                <small>
                    Um arquivo por envio.
                    Tamanho máximo: 10 MiB.
                    Não envie PDF protegido por senha.
                </small>
            </div>

            <div class="anexo-acoes">
                <button class="anexo-botao" type="submit">
                    Enviar PDF
                </button>
            </div>
        </form>
    </section>
{% endif %}

<div class="anexo-ajuda">
    Os documentos ficam associados a esta ordem de serviço,
    mesmo que o equipamento ainda não esteja vinculado.
    Vincular o equipamento posteriormente não exige reenviar
    os arquivos.
</div>

<section class="painel anexo-tabela-container">
    <h2>Documentos anexados</h2>

    <table class="anexo-tabela">
        <thead>
            <tr>
                <th scope="col">Arquivo</th>
                <th scope="col">Tamanho</th>
                <th scope="col">Enviado por</th>
                <th scope="col">Data de envio</th>
                <th scope="col">Ação</th>
            </tr>
        </thead>

        <tbody>
            {% for anexo in anexos %}
                <tr>
                    <td>{{ anexo["nome_original"] }}</td>

                    <td>
                        {{ "%.2f"|format(
                            anexo["tamanho_bytes"] / 1048576
                        ) }} MiB
                    </td>

                    <td>{{ anexo["usuario_nome"] }}</td>

                    <td>{{ anexo["criado_em"] }}</td>

                    <td>
                        <a href="{{ url_for(
                            'ordens_anexo_download',
                            id_anexo=anexo['id_anexo']
                        ) }}">
                            Baixar PDF
                        </a>
                    </td>
                </tr>
            {% else %}
                <tr>
                    <td colspan="5">
                        Nenhum documento anexado.
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</section>
{% endblock %}
"""


def registrar_anexos_os(
    app,
    get_db,
    login_obrigatorio,
):
    """Registra envio e download protegido dos PDFs de OS."""

    pasta_anexos = Path(app.instance_path) / "documentos_os"
    pasta_anexos.mkdir(parents=True, exist_ok=True)
    pasta_anexos = pasta_anexos.resolve()

    limite_atual = app.config.get("MAX_CONTENT_LENGTH")

    if limite_atual is None:
        app.config["MAX_CONTENT_LENGTH"] = LIMITE_REQUISICAO_BYTES
    else:
        app.config["MAX_CONTENT_LENGTH"] = min(
            limite_atual,
            LIMITE_REQUISICAO_BYTES,
        )

    def eh_administrador():
        return (
            g.usuario is not None
            and g.usuario["papel"] == "administrador_principal"
        )

    def buscar_ordem(id_os):
        return get_db().execute(
            """
            SELECT
                o.*,
                u.nome AS unidade_nome,
                e.descricao AS equipamento_nome,
                e.patrimonio AS equipamento_patrimonio
            FROM ordens_servico o
            JOIN unidades u
                ON u.id_unidade = o.id_unidade
            LEFT JOIN equipamentos e
                ON e.id_equipamento = o.id_equipamento
            WHERE o.id_os = ?
            """,
            (id_os,),
        ).fetchone()

    def validar_arquivo(arquivo):
        if arquivo is None or not arquivo.filename:
            return None, None, "Selecione um arquivo PDF."

        nome_original = (
            arquivo.filename
            .replace("\\", "/")
            .rsplit("/", 1)[-1]
            .strip()
        )

        nome_original = "".join(
            caractere
            for caractere in nome_original
            if caractere.isprintable()
        )

        if not nome_original or len(nome_original) > 200:
            return (
                None,
                None,
                "O nome do arquivo deve ter até 200 caracteres.",
            )

        if Path(nome_original).suffix.lower() != ".pdf":
            return None, None, "Envie um arquivo com extensão .pdf."

        conteudo = arquivo.stream.read(LIMITE_PDF_BYTES + 1)

        if not conteudo:
            return None, None, "O arquivo está vazio."

        if len(conteudo) > LIMITE_PDF_BYTES:
            return None, None, "O PDF excede o limite de 10 MiB."

        if not conteudo.startswith(b"%PDF-"):
            return (
                None,
                None,
                "O arquivo não possui um cabeçalho PDF válido.",
            )

        try:
            leitor = PdfReader(BytesIO(conteudo), strict=False)

            if leitor.is_encrypted:
                return (
                    None,
                    None,
                    "Não são aceitos PDFs protegidos por senha "
                    "ou criptografados.",
                )

            if len(leitor.pages) == 0:
                return None, None, "O PDF não contém páginas."

        except Exception:
            app.logger.warning(
                "PDF rejeitado durante a validação",
                exc_info=True,
            )

            return (
                None,
                None,
                "Não foi possível ler o PDF. "
                "Confira se ele está íntegro e sem senha.",
            )

        return nome_original, conteudo, None

    @app.route(
        "/ordens-servico/<int:id_os>/anexos",
        methods=["GET", "POST"],
    )
    @login_obrigatorio
    def ordens_anexos(id_os):
        db = get_db()
        ordem = buscar_ordem(id_os)

        if ordem is None:
            abort(404)

        erro = None

        if request.method == "POST":
            if not eh_administrador():
                abort(403)

            arquivo = request.files.get("arquivo")

            nome_original, conteudo, erro = validar_arquivo(arquivo)

            if erro is None:
                nome_armazenado = f"{uuid4().hex}.pdf"
                destino = pasta_anexos / nome_armazenado
                arquivo_criado = False

                try:
                    with destino.open("xb") as saida:
                        arquivo_criado = True
                        saida.write(conteudo)

                    db.execute(
                        """
                        INSERT INTO anexos_os (
                            id_os,
                            nome_original,
                            nome_armazenado,
                            tamanho_bytes,
                            enviado_por
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            id_os,
                            nome_original,
                            nome_armazenado,
                            len(conteudo),
                            g.usuario["id_usuario"],
                        ),
                    )

                    db.execute(
                        """
                        UPDATE ordens_servico
                        SET atualizado_por = ?,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id_os = ?
                        """,
                        (g.usuario["id_usuario"], id_os),
                    )

                    db.commit()

                except (OSError, sqlite3.Error):
                    db.rollback()

                    if arquivo_criado:
                        try:
                            destino.unlink(missing_ok=True)
                        except OSError:
                            app.logger.exception(
                                "Não foi possível remover "
                                "arquivo após falha no envio"
                            )

                    app.logger.exception("Erro ao salvar anexo da OS")

                    erro = (
                        "Não foi possível salvar o documento. "
                        "Confira o erro no terminal."
                    )

                else:
                    flash("Documento anexado com sucesso.", "sucesso")

                    return redirect(
                        url_for("ordens_anexos", id_os=id_os)
                    )

        anexos = db.execute(
            """
            SELECT
                a.*,
                u.nome AS usuario_nome
            FROM anexos_os a
            JOIN usuarios u
                ON u.id_usuario = a.enviado_por
            WHERE a.id_os = ?
            ORDER BY a.criado_em DESC,
                     a.id_anexo DESC
            """,
            (id_os,),
        ).fetchall()

        resposta = app.make_response(
            render_template_string(
                PAGINA_ANEXOS_HTML,
                ordem=ordem,
                anexos=anexos,
                administrador=eh_administrador(),
                erro=erro,
            )
        )

        resposta.headers["Cache-Control"] = "no-store"

        return resposta

    @app.get(
        "/ordens-servico/anexos/<int:id_anexo>/download"
    )
    @login_obrigatorio
    def ordens_anexo_download(id_anexo):
        anexo = get_db().execute(
            """
            SELECT a.*
            FROM anexos_os a
            JOIN ordens_servico o
                ON o.id_os = a.id_os
            WHERE a.id_anexo = ?
            """,
            (id_anexo,),
        ).fetchone()

        if anexo is None:
            abort(404)

        nome_armazenado = anexo["nome_armazenado"]

        if not PADRAO_NOME_INTERNO.fullmatch(nome_armazenado):
            abort(404)

        caminho = (pasta_anexos / nome_armazenado).resolve()

        if caminho.parent != pasta_anexos or not caminho.is_file():
            abort(404)

        nome_download = secure_filename(anexo["nome_original"])

        if not nome_download.lower().endswith(".pdf"):
            nome_download = f"documento-os-{id_anexo}.pdf"

        resposta = send_file(
            caminho,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nome_download,
            conditional=False,
            etag=False,
        )

        resposta.headers["Cache-Control"] = (
            "private, no-store, max-age=0"
        )
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Content-Security-Policy"] = "sandbox"

        return resposta