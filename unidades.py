import sqlite3
from functools import wraps

import click
from flask import (
    abort,
    flash,
    g,
    redirect,
    render_template_string,
    request,
    url_for,
)


CATEGORIAS = (
    "Atenção Básica",
    "Urgência e Emergência",
    "Centros de Especialidades e Clínicas",
    "Saúde Mental",
    "Programas Especiais e Suporte",
    "Estabelecimentos penitenciários",
)

UNIDADES_INICIAIS = {
    "Atenção Básica": [
        "USF Santa Rita",
        "USF Interlagos",
        "USF Jardim Maristela",
        "USF Vila Nova",
        "USF Santo André",
        "USF Jardim Atenas",
        "USF Arapuá",
        "USF Vila Haro",
        "USF Vila Piloto",
        "USF Paranapungá",
        "USF Joel Neves da Silva",
        "USF Jupiá",
        "USF Nova Três Lagoas",
        "USF Santa Luzia",
        "USF Novo Oeste",
        "USF Vila Alegre",
        "USF Chácara Eldorado",
    ],
    "Urgência e Emergência": [
        "UPA 24h",
        "SAMU 192",
    ],
    "Centros de Especialidades e Clínicas": [
        "CEM Dr. Júlio Maia",
        "CEO",
        "Clínica da Criança Dr. Carlos Azambuja Leão Junior",
        "Clínica da Mulher",
        "Clínica Ortopédica Municipal Dr. Paulo Baccaro Filho",
        "Clínica do Idoso e Reabilitação",
        "Clínica de Fisioterapia e Reabilitação Municipal",
    ],
    "Saúde Mental": [
        "CAPS II",
        "CAPS AD",
        "Ambulatório Especializado de Saúde Mental",
        "Residência Terapêutica",
    ],
    "Programas Especiais e Suporte": [
        "SAD",
        "Programa IST/AIDS e Hepatites Virais",
    ],
    "Estabelecimentos penitenciários": [
        "Colônia Penal Industrial Paracelso de Lima Vieira Jesus",
        "Estabelecimento Penal Feminino de Três Lagoas",
        "Penitenciária de Três Lagoas",
    ],
}


# Estilos restritos ao módulo, sem substituir seu style.css.
ESTILO = """
<style>
    .unidades-acoes {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        margin: 20px 0;
    }

    .unidades-botao {
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

    .unidades-botao--secundario {
        background: #475569;
    }

    .unidades-filtro,
    .unidades-formulario {
        display: grid;
        gap: 16px;
    }

    .unidades-filtro {
        grid-template-columns: repeat(
            auto-fit, minmax(180px, 1fr)
        );
        align-items: end;
        margin: 20px 0;
    }

    .unidades-campo label {
        display: block;
        margin-bottom: 6px;
        font-weight: 600;
    }

    .unidades-campo input,
    .unidades-campo select,
    .unidades-campo textarea {
        width: 100%;
        padding: 10px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: white;
        color: #1e293b;
        font: inherit;
    }

    .unidades-tabela-container {
        overflow-x: auto;
    }

    .unidades-tabela {
        width: 100%;
        border-collapse: collapse;
    }

    .unidades-tabela th,
    .unidades-tabela td {
        padding: 12px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
        vertical-align: top;
    }

    .unidades-tabela th {
        background: #f1f5f9;
    }

    .unidades-erros {
        padding: 16px 32px;
        background: #fee2e2;
        color: #991b1b;
        border-radius: 6px;
    }
</style>
"""


LISTA_HTML = """
{% extends "base.html" %}

{% block title %}
    Unidades | Gestão de Equipamentos Clínicos
{% endblock %}

{% block extra_head %}
""" + ESTILO + """
{% endblock %}

{% block content %}
<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">REDE MUNICIPAL</p>
        <h1>Unidades</h1>
        <p class="descricao">
            Consulte as unidades e mantenha seus dados atualizados.
        </p>
    </div>
</section>

<div class="unidades-acoes">
    <span>{{ unidades|length }} unidade(s) encontrada(s)</span>

    {% if administrador %}
        <a class="unidades-botao"
           href="{{ url_for('unidades_nova') }}">
            Cadastrar unidade
        </a>
    {% endif %}
</div>

<form class="unidades-filtro" method="get"
      action="{{ url_for('unidades_lista') }}">
    <div class="unidades-campo">
        <label for="q">Nome ou CNES</label>
        <input id="q" name="q" value="{{ busca }}"
               maxlength="200" placeholder="Pesquisar">
    </div>

    <div class="unidades-campo">
        <label for="categoria">Categoria</label>
        <select id="categoria" name="categoria">
            <option value="">Todas</option>
            {% for item in categorias %}
                <option value="{{ item }}"
                    {% if categoria == item %}selected{% endif %}>
                    {{ item }}
                </option>
            {% endfor %}
        </select>
    </div>

    <div class="unidades-campo">
        <label for="situacao">Situação</label>
        <select id="situacao" name="situacao">
            <option value=""
                {% if situacao == '' %}selected{% endif %}>
                Todas
            </option>
            <option value="1"
                {% if situacao == '1' %}selected{% endif %}>
                Ativas
            </option>
            <option value="0"
                {% if situacao == '0' %}selected{% endif %}>
                Inativas
            </option>
        </select>
    </div>

    <div class="unidades-acoes">
        <button class="unidades-botao" type="submit">
            Filtrar
        </button>
        <a href="{{ url_for('unidades_lista') }}">Limpar</a>
    </div>
</form>

<div class="painel unidades-tabela-container">
    <table class="unidades-tabela">
        <thead>
            <tr>
                <th scope="col">Unidade</th>
                <th scope="col">Categoria</th>
                <th scope="col">CNES</th>
                <th scope="col">Situação</th>
                <th scope="col">Ação</th>
            </tr>
        </thead>
        <tbody>
            {% for unidade in unidades %}
                <tr>
                    <td>{{ unidade["nome"] }}</td>
                    <td>{{ unidade["categoria"] }}</td>
                    <td>{{ unidade["cnes"] or "Não informado" }}</td>
                    <td>
                        {{ "Ativa" if unidade["ativo"] else "Inativa" }}
                    </td>
                    <td>
                        <a href="{{ url_for(
                            'unidades_editar',
                            id_unidade=unidade['id_unidade']
                        ) }}">
                            {{ "Editar" if administrador else "Visualizar" }}
                        </a>
                    </td>
                </tr>
            {% else %}
                <tr>
                    <td colspan="5">
                        Nenhuma unidade encontrada.
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""


FORMULARIO_HTML = """
{% extends "base.html" %}

{% block title %}
    {{ titulo }} | Gestão de Equipamentos Clínicos
{% endblock %}

{% block extra_head %}
""" + ESTILO + """
{% endblock %}

{% block content %}
<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">REDE MUNICIPAL</p>
        <h1>{{ titulo }}</h1>
        <p class="descricao">
            Campos com * são obrigatórios.
        </p>
    </div>
</section>

{% if erros %}
    <ul class="unidades-erros" role="alert">
        {% for erro in erros %}
            <li>{{ erro }}</li>
        {% endfor %}
    </ul>
{% endif %}

<form class="painel unidades-formulario" method="post">
    <input type="hidden" name="_csrf_token"
           value="{{ csrf_token() }}">

    <fieldset {% if not administrador %}disabled{% endif %}
              style="border:0; padding:0; min-width:0;">
        <div class="unidades-formulario">
            <div class="unidades-campo">
                <label for="nome">Nome da unidade *</label>
                <input id="nome" name="nome"
                       value="{{ dados['nome'] }}"
                       maxlength="200" required>
            </div>

            <div class="unidades-campo">
                <label for="categoria">Categoria *</label>
                <select id="categoria" name="categoria" required>
                    {% for item in categorias %}
                        <option value="{{ item }}"
                            {% if dados['categoria'] == item %}
                                selected
                            {% endif %}>
                            {{ item }}
                        </option>
                    {% endfor %}
                </select>
            </div>

            {% for campo, rotulo, tipo, limite in campos %}
                <div class="unidades-campo">
                    <label for="{{ campo }}">{{ rotulo }}</label>
                    <input id="{{ campo }}" name="{{ campo }}"
                           type="{{ tipo }}"
                           maxlength="{{ limite }}"
                           value="{{ dados[campo] }}">
                </div>
            {% endfor %}

            <div class="unidades-campo">
                <label for="observacoes">Observações</label>
                <textarea id="observacoes" name="observacoes"
                          rows="4" maxlength="5000"
                >{{ dados["observacoes"] }}</textarea>
            </div>

            <div class="unidades-campo">
                <label for="ativo">Situação *</label>
                <select id="ativo" name="ativo" required>
                    <option value="1"
                        {% if dados['ativo'] == '1' %}selected{% endif %}>
                        Ativa
                    </option>
                    <option value="0"
                        {% if dados['ativo'] == '0' %}selected{% endif %}>
                        Inativa
                    </option>
                </select>
            </div>
        </div>
    </fieldset>

    <div class="unidades-acoes">
        {% if administrador %}
            <button class="unidades-botao" type="submit">
                Salvar unidade
            </button>
        {% endif %}

        <a class="unidades-botao unidades-botao--secundario"
           href="{{ url_for('unidades_lista') }}">
            Voltar à lista
        </a>
    </div>
</form>
{% endblock %}
"""


CAMPOS = (
    ("cnes", "CNES", "text", 20),
    ("endereco", "Endereço", "text", 300),
    ("bairro", "Bairro", "text", 150),
    ("telefone", "Telefone", "tel", 40),
    ("email", "E-mail", "email", 254),
    ("responsavel", "Responsável", "text", 200),
)

COLUNAS = (
    "nome",
    "categoria",
    "cnes",
    "endereco",
    "bairro",
    "telefone",
    "email",
    "responsavel",
    "observacoes",
    "ativo",
)


def registrar_unidades(app, get_db, login_obrigatorio):
    """Registra o módulo na aplicação existente."""

    def eh_administrador():
        return (
            g.usuario is not None
            and g.usuario["papel"] == "administrador_principal"
        )

    def administrador_obrigatorio(funcao):
        @wraps(funcao)
        def verificar(*args, **kwargs):
            if not eh_administrador():
                abort(403)
            return funcao(*args, **kwargs)

        return verificar

    @app.cli.command("inicializar-unidades")
    def inicializar_unidades():
        """Cria a tabela e inclui as 35 unidades iniciais."""

        db = get_db()

        try:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS unidades (
                    id_unidade INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_origem TEXT UNIQUE,
                    nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    categoria TEXT NOT NULL,
                    cnes TEXT NOT NULL DEFAULT '',
                    endereco TEXT NOT NULL DEFAULT '',
                    bairro TEXT NOT NULL DEFAULT '',
                    telefone TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    responsavel TEXT NOT NULL DEFAULT '',
                    observacoes TEXT NOT NULL DEFAULT '',
                    ativo INTEGER NOT NULL DEFAULT 1
                        CHECK (ativo IN (0, 1)),
                    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            inseridas = 0
            numero = 0

            for categoria, nomes in UNIDADES_INICIAIS.items():
                for nome in nomes:
                    numero += 1

                    # Identificador permanente da carga inicial.
                    # Não depende do nome após uma edição.
                    codigo = f"prototipo-unidade-{numero:03d}"

                    resultado = db.execute(
                        """
                        INSERT INTO unidades (
                            codigo_origem, nome, categoria
                        )
                        VALUES (?, ?, ?)
                        ON CONFLICT(codigo_origem) DO NOTHING
                        """,
                        (codigo, nome, categoria),
                    )

                    inseridas += resultado.rowcount

            db.commit()

        except sqlite3.Error as erro:
            db.rollback()
            raise click.ClickException(
                f"Não foi possível inicializar as unidades: {erro}"
            ) from erro

        total = db.execute(
            "SELECT COUNT(*) FROM unidades"
        ).fetchone()[0]

        click.echo(f"Unidades incluídas agora: {inseridas}")
        click.echo(f"Total de unidades no banco: {total}")
        click.echo("Unidades existentes e editadas foram preservadas.")

    def ler_formulario():
        dados = {
            coluna: request.form.get(coluna, "").strip()
            for coluna in COLUNAS
        }

        erros = []

        if not dados["nome"]:
            erros.append("Informe o nome da unidade.")
        elif len(dados["nome"]) > 200:
            erros.append("O nome deve ter até 200 caracteres.")

        if dados["categoria"] not in CATEGORIAS:
            erros.append("Selecione uma categoria válida.")

        if dados["ativo"] not in ("0", "1"):
            erros.append("Selecione uma situação válida.")

        for campo, rotulo, tipo, limite in CAMPOS:
            if len(dados[campo]) > limite:
                erros.append(
                    f"{rotulo}: use no máximo {limite} caracteres."
                )

        if len(dados["observacoes"]) > 5000:
            erros.append(
                "As observações devem ter até 5000 caracteres."
            )

        if dados["email"]:
            partes = dados["email"].split("@")

            if (
                len(partes) != 2
                or not partes[0]
                or not partes[1]
                or any(c.isspace() for c in dados["email"])
            ):
                erros.append("Informe um e-mail válido.")

        return dados, erros

    def mostrar_formulario(dados, erros, titulo):
        return render_template_string(
            FORMULARIO_HTML,
            titulo=titulo,
            dados=dados,
            erros=erros,
            categorias=CATEGORIAS,
            campos=CAMPOS,
            administrador=eh_administrador(),
        )

    @app.get("/unidades")
    @login_obrigatorio
    def unidades_lista():
        busca = request.args.get("q", "").strip()[:200]
        categoria = request.args.get("categoria", "")
        situacao = request.args.get("situacao", "")

        condicoes = []
        parametros = []

        if busca:
            condicoes.append(
                "(instr(lower(nome), lower(?)) > 0 "
                "OR instr(cnes, ?) > 0)"
            )
            parametros.extend((busca, busca))

        if categoria in CATEGORIAS:
            condicoes.append("categoria = ?")
            parametros.append(categoria)
        else:
            categoria = ""

        if situacao in ("0", "1"):
            condicoes.append("ativo = ?")
            parametros.append(int(situacao))
        else:
            situacao = ""

        sql = "SELECT * FROM unidades"

        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)

        sql += " ORDER BY categoria, nome COLLATE NOCASE"

        unidades = get_db().execute(
            sql, parametros
        ).fetchall()

        return render_template_string(
            LISTA_HTML,
            unidades=unidades,
            categorias=CATEGORIAS,
            busca=busca,
            categoria=categoria,
            situacao=situacao,
            administrador=eh_administrador(),
        )

    @app.route("/unidades/nova", methods=["GET", "POST"])
    @login_obrigatorio
    @administrador_obrigatorio
    def unidades_nova():
        dados = {coluna: "" for coluna in COLUNAS}
        dados["categoria"] = CATEGORIAS[0]
        dados["ativo"] = "1"
        erros = []

        if request.method == "POST":
            dados, erros = ler_formulario()

            if not erros:
                db = get_db()

                try:
                    db.execute(
                        """
                        INSERT INTO unidades (
                            nome, categoria, cnes, endereco,
                            bairro, telefone, email, responsavel,
                            observacoes, ativo
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        tuple(dados[coluna] for coluna in COLUNAS),
                    )
                    db.commit()

                except sqlite3.IntegrityError:
                    db.rollback()
                    erros.append(
                        "Não foi possível cadastrar. "
                        "Verifique se já existe uma unidade "
                        "com esse nome."
                    )

                else:
                    flash(
                        "Unidade cadastrada com sucesso.",
                        "sucesso",
                    )
                    return redirect(url_for("unidades_lista"))

        return mostrar_formulario(
            dados, erros, "Cadastrar unidade"
        )

    @app.route(
        "/unidades/<int:id_unidade>/editar",
        methods=["GET", "POST"],
    )
    @login_obrigatorio
    def unidades_editar(id_unidade):
        db = get_db()

        unidade = db.execute(
            """
            SELECT *
            FROM unidades
            WHERE id_unidade = ?
            """,
            (id_unidade,),
        ).fetchone()

        if unidade is None:
            abort(404)

        if request.method == "POST" and not eh_administrador():
            abort(403)

        dados = {
            coluna: str(unidade[coluna])
            for coluna in COLUNAS
        }
        erros = []

        if request.method == "POST":
            dados, erros = ler_formulario()

            if not erros:
                try:
                    db.execute(
                        """
                        UPDATE unidades
                        SET nome = ?,
                            categoria = ?,
                            cnes = ?,
                            endereco = ?,
                            bairro = ?,
                            telefone = ?,
                            email = ?,
                            responsavel = ?,
                            observacoes = ?,
                            ativo = ?,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id_unidade = ?
                        """,
                        tuple(
                            dados[coluna] for coluna in COLUNAS
                        ) + (id_unidade,),
                    )
                    db.commit()

                except sqlite3.IntegrityError:
                    db.rollback()
                    erros.append(
                        "Não foi possível salvar. "
                        "Verifique se outra unidade já usa "
                        "esse nome."
                    )

                else:
                    flash(
                        "Unidade atualizada com sucesso.",
                        "sucesso",
                    )
                    return redirect(url_for("unidades_lista"))

        titulo = (
            "Editar unidade"
            if eh_administrador()
            else "Visualizar unidade"
        )

        return mostrar_formulario(dados, erros, titulo)


