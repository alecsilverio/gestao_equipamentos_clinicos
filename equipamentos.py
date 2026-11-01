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


SITUACOES = (
    "Não informado",
    "Em uso",
    "Em manutenção",
    "Inativo",
    "Baixado",
)

CAMPOS = (
    ("descricao", "Descrição do equipamento", 200),
    ("patrimonio", "Número de patrimônio", 80),
    ("marca", "Marca", 120),
    ("modelo", "Modelo", 150),
    ("numero_serie", "Número de série", 150),
    ("setor", "Setor / sala", 150),
    ("referencias_os", "Referências de ordens de serviço", 500),
)

COLUNAS = (
    "id_unidade",
    "descricao",
    "patrimonio",
    "marca",
    "modelo",
    "numero_serie",
    "setor",
    "situacao",
    "referencias_os",
    "observacoes",
)

SQL_INDICE_PATRIMONIO = """
CREATE UNIQUE INDEX IF NOT EXISTS
uq_equipamentos_patrimonio_preenchido
ON equipamentos (UPPER(TRIM(patrimonio)))
WHERE TRIM(patrimonio) <> ''
"""


ESTILO = """
<style>
    .equip-acoes,
    .equip-paginacao {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 12px;
        margin: 18px 0;
    }

    .equip-botao {
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

    .equip-botao--secundario {
        background: #475569;
    }

    .equip-botao--perigo {
        background: #b91c1c;
    }

    .equip-link-perigo {
        color: #b91c1c;
    }

    .equip-grade {
        display: grid;
        grid-template-columns: repeat(
            auto-fit, minmax(220px, 1fr)
        );
        gap: 18px;
    }

    .equip-campo label {
        display: block;
        margin-bottom: 6px;
        font-weight: 600;
    }

    .equip-campo input,
    .equip-campo select,
    .equip-campo textarea {
        width: 100%;
        padding: 11px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: white;
        color: #1e293b;
        font: inherit;
        box-sizing: border-box;
    }

    .equip-campo--inteiro {
        grid-column: 1 / -1;
    }

    .equip-campo small,
    .equip-tabela small {
        display: block;
        margin-top: 6px;
        color: #475569;
    }

    .equip-tabela-container {
        overflow-x: auto;
    }

    .equip-tabela {
        width: 100%;
        border-collapse: collapse;
    }

    .equip-tabela th,
    .equip-tabela td {
        padding: 12px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
        vertical-align: top;
    }

    .equip-tabela th {
        background: #f1f5f9;
    }

    .equip-erros,
    .equip-alerta {
        padding: 16px;
        border-radius: 6px;
        color: #991b1b;
        background: #fee2e2;
        margin-bottom: 18px;
    }

    .equip-erros {
        padding-left: 32px;
    }

    .equip-ajuda {
        padding: 14px;
        margin-bottom: 20px;
        border-radius: 6px;
        background: #e0f2fe;
        color: #0c4a6e;
    }

    .equip-dados dt {
        margin-top: 14px;
        font-weight: 600;
    }

    .equip-dados dd {
        margin: 5px 0 0;
        overflow-wrap: anywhere;
    }

    .equip-confirmacao {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-top: 24px;
    }
</style>
"""


LISTA_HTML = (
    """
{% extends "base.html" %}
{% block title %}
    Equipamentos | Gestão de Equipamentos Clínicos
{% endblock %}
{% block extra_head %}
"""
    + ESTILO
    + """
{% endblock %}
{% block content %}

<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">INVENTÁRIO</p>
        <h1>Equipamentos</h1>
        <p class="descricao">
            Consulte os equipamentos e seus dados cadastrais.
        </p>
    </div>
</section>

<div class="equip-acoes">
    <span>{{ total }} equipamento(s) encontrado(s)</span>

    {% if administrador %}
        <a class="equip-botao"
            href="{{ url_for('equipamentos_novo') }}">
            Cadastrar equipamento
        </a>
    {% endif %}
</div>

{% if filtro_manutencao %}
    <div class="equip-ajuda">
        Exibindo equipamentos em manutenção: com essa situação
        no cadastro ou com OS em andamento.
        <a href="{{ url_for('equipamentos_lista') }}">Ver todos</a>
    </div>
{% endif %}

{% if filtro_manutencao %}
    <div class="equip-ajuda">
        Exibindo equipamentos em manutenção: com essa situação
        no cadastro ou com OS em andamento.
        <a href="{{ url_for('equipamentos_lista') }}">Ver todos</a>
    </div>
{% endif %}

<form method="get"
    action="{{ url_for('equipamentos_lista') }}"
    class="painel">

    {% if filtro_manutencao %}
        <input type="hidden"
        name="em_manutencao"
        value="{{ filtro_manutencao }}">
    {% endif %}

    {% if filtro_manutencao %}
        <input type="hidden"
                name="em_manutencao"
                value="{{ filtro_manutencao }}">
    {% endif %}

    <div class="equip-grade">
        <div class="equip-campo">
            <label for="q">Pesquisar</label>
            <input id="q" name="q"
                    value="{{ busca }}"
                    maxlength="200"
                    placeholder="Descrição, patrimônio, marca, modelo ou série">
        </div>

        <div class="equip-campo">
            <label for="id_unidade">Unidade</label>
            <select id="id_unidade" name="id_unidade">
                <option value="">Todas as unidades</option>

                {% for unidade in unidades %}
                    <option value="{{ unidade['id_unidade'] }}"
                        {% if filtro_unidade == unidade['id_unidade'] %}
                            selected
                        {% endif %}>
                        {{ unidade["nome"] }}
                        {% if not unidade["ativo"] %}
                            — Inativa
                        {% endif %}
                    </option>
                {% endfor %}
            </select>
        </div>

        <div class="equip-campo">
            <label for="situacao">Situação</label>
            <select id="situacao" name="situacao">
                <option value="">Todas</option>

                {% for item in situacoes %}
                    <option value="{{ item }}"
                        {% if filtro_situacao == item %}
                            selected
                        {% endif %}>
                        {{ item }}
                    </option>
                {% endfor %}
            </select>
        </div>
    </div>

    <div class="equip-acoes">
        <button class="equip-botao" type="submit">
            Filtrar
        </button>
        <a href="{{ url_for('equipamentos_lista') }}">
            Limpar
        </a>
    </div>
</form>

<div class="painel equip-tabela-container">
    <table class="equip-tabela">
        <thead>
            <tr>
                <th scope="col">Equipamento</th>
                <th scope="col">Patrimônio</th>
                <th scope="col">Unidade / setor</th>
                <th scope="col">Situação</th>
                <th scope="col">Ações</th>
            </tr>
        </thead>

        <tbody>
            {% for item in equipamentos %}
                <tr>
                    <td>
                        {{ item["descricao"] }}
                        <small>ID: {{ item["id_equipamento"] }}</small>
                        <small>
                            Marca: {{ item["marca"] or "Não informada" }}
                        </small>
                        <small>
                            Modelo: {{ item["modelo"] or "Não informado" }}
                        </small>
                        <small>
                            Série: {{ item["numero_serie"] or "Não informada" }}
                        </small>
                    </td>

                    <td>
                        {{ item["patrimonio"] or "Não informado" }}
                    </td>

                    <td>
                        {{ item["unidade_nome"] }}
                        <small>
                            {{ item["setor"] or "Setor não informado" }}
                        </small>
                    </td>

                    <td>
                        {{ item["situacao"] }}

                        {% if item["os_em_andamento"]
                                and item["situacao"] != "Em manutenção" %}
                            <small>Em manutenção: há OS em andamento</small>
                        {% endif %}
                    </td>

                    <td>
                        <div class="equip-acoes">
                            <a href="{{ url_for(
                                'equipamentos_editar',
                                id_equipamento=item['id_equipamento']
                            ) }}">
                                {{ "Editar" if administrador else "Visualizar" }}
                            </a>

                            <a href="{{ url_for(
                                'ordens_lista',
                                id_equipamento=item['id_equipamento']
                            ) }}">
                                OS ({{ item["total_os"] }})
                            </a>

                            {% if administrador %}
                                <a class="equip-link-perigo"
                                    href="{{ url_for(
                                        'equipamentos_excluir',
                                        id_equipamento=item['id_equipamento']
                                    ) }}">
                                    Excluir
                                </a>
                            {% endif %}
                        </div>
                    </td>
                </tr>
            {% else %}
                <tr>
                    <td colspan="5">
                        Nenhum equipamento encontrado.
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<nav class="equip-paginacao" aria-label="Paginação">
    {% if pagina > 1 %}
        <a href="{{ url_for(
            'equipamentos_lista',
            q=busca,
            id_unidade=filtro_unidade or '',
            situacao=filtro_situacao,
            pagina=pagina-1
        ) }}">
            Anterior
        </a>
    {% endif %}

    <span>Página {{ pagina }} de {{ paginas }}</span>

    {% if pagina < paginas %}
        <a href="{{ url_for(
            'equipamentos_lista',
            q=busca,
            id_unidade=filtro_unidade or '',
            situacao=filtro_situacao,
            pagina=pagina+1
        ) }}">
            Próxima
        </a>
    {% endif %}
</nav>

{% endblock %}
"""
)


FORMULARIO_HTML = (
    """
{% extends "base.html" %}
{% block title %}
    {{ titulo }} | Gestão de Equipamentos Clínicos
{% endblock %}
{% block extra_head %}
"""
    + ESTILO
    + """
{% endblock %}
{% block content %}

<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">INVENTÁRIO</p>
        <h1>{{ titulo }}</h1>
        <p class="descricao">
            Campos com * são obrigatórios.
        </p>
    </div>
</section>

{% if erros %}
    <ul class="equip-erros" role="alert">
        {% for erro in erros %}
            <li>{{ erro }}</li>
        {% endfor %}
    </ul>
{% endif %}

{% if administrador %}
    <div class="equip-ajuda">
        O patrimônio preenchido deve ser exclusivo em todo
        o sistema. Se não houver número, deixe o campo vazio.
        Não utilize SP ou SEM PATRIMÔNIO.
        As referências de OS não criam atendimentos automaticamente.
    </div>
{% endif %}

<form method="post" class="painel">
    <input type="hidden"
           name="_csrf_token"
           value="{{ csrf_token() }}">

    <fieldset {% if not administrador %}disabled{% endif %}
              style="border:0; padding:0; min-width:0;">

        <div class="equip-grade">
            <div class="equip-campo equip-campo--inteiro">
                <label for="id_unidade">Unidade *</label>

                <select id="id_unidade"
                        name="id_unidade"
                        required>
                    <option value="">Selecione</option>

                    {% for unidade in unidades %}
                        <option value="{{ unidade['id_unidade'] }}"
                            {% if dados['id_unidade'] == (unidade['id_unidade']|string) %}
                                selected
                            {% endif %}>
                            {{ unidade["nome"] }}
                            {% if not unidade["ativo"] %}
                                — Inativa
                            {% endif %}
                        </option>
                    {% endfor %}
                </select>
            </div>

            {% for campo, rotulo, limite in campos %}
                <div class="equip-campo">
                    <label for="{{ campo }}">
                        {{ rotulo }}
                        {% if campo == "descricao" %}*{% endif %}
                    </label>

                    <input id="{{ campo }}"
                            name="{{ campo }}"
                            value="{{ dados[campo] }}"
                            maxlength="{{ limite }}"
                            {% if campo == "descricao" %}required{% endif %}>

                    {% if campo == "patrimonio" %}
                        <small>
                            Exclusivo. Deixe vazio se não houver número.
                        </small>
                    {% endif %}

                    {% if campo == "referencias_os" %}
                        <small>
                            Exemplo: 3052; 2982.
                            Apenas referências históricas.
                        </small>
                    {% endif %}
                </div>
            {% endfor %}

            <div class="equip-campo">
                <label for="situacao">Situação *</label>

                <select id="situacao" name="situacao" required>
                    {% for item in situacoes %}
                        <option value="{{ item }}"
                            {% if dados['situacao'] == item %}
                                selected
                            {% endif %}>
                            {{ item }}
                        </option>
                    {% endfor %}
                </select>
            </div>

            <div class="equip-campo equip-campo--inteiro">
                <label for="observacoes">Observações</label>

                <textarea id="observacoes"
                            name="observacoes"
                            rows="5"
                            maxlength="5000"
                >{{ dados["observacoes"] }}</textarea>
            </div>
        </div>
    </fieldset>

    <div class="equip-acoes">
        {% if administrador %}
            <button class="equip-botao" type="submit">
                Salvar equipamento
            </button>
        {% endif %}

        <a class="equip-botao equip-botao--secundario"
            href="{{ url_for('equipamentos_lista') }}">
            Voltar à lista
        </a>
    </div>
</form>

{% if administrador and id_equipamento %}
    <div class="equip-acoes">
        <a class="equip-botao equip-botao--perigo"
            href="{{ url_for(
                'equipamentos_excluir',
                id_equipamento=id_equipamento
            ) }}">
            Excluir este cadastro
        </a>
    </div>
{% endif %}

{% endblock %}
"""
)


EXCLUIR_HTML = (
    """
{% extends "base.html" %}
{% block title %}
    Excluir equipamento | Gestão de Equipamentos Clínicos
{% endblock %}
{% block extra_head %}
"""
    + ESTILO
    + """
{% endblock %}
{% block content %}

<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">ADMINISTRAÇÃO DO INVENTÁRIO</p>
        <h1>Confirmar exclusão</h1>
    </div>
</section>

<div class="equip-alerta" role="alert">
    A exclusão é definitiva.
    Utilize esta função somente para cadastros incorretos
    ou duplicados. Para um equipamento real que saiu de uso,
    prefira editar sua situação para Inativo ou Baixado.
</div>

{% if erro %}
    <div class="equip-alerta" role="alert">
        {{ erro }}
    </div>
{% endif %}

<div class="painel">
    <dl class="equip-dados">
        <dt>ID do cadastro</dt>
        <dd>{{ equipamento["id_equipamento"] }}</dd>

        <dt>Equipamento</dt>
        <dd>{{ equipamento["descricao"] }}</dd>

        <dt>Patrimônio</dt>
        <dd>{{ equipamento["patrimonio"] or "Não informado" }}</dd>

        <dt>Unidade</dt>
        <dd>{{ equipamento["unidade_nome"] }}</dd>

        <dt>Setor</dt>
        <dd>{{ equipamento["setor"] or "Não informado" }}</dd>

        <dt>Marca / modelo</dt>
        <dd>
            {{ equipamento["marca"] or "Não informada" }}
            /
            {{ equipamento["modelo"] or "Não informado" }}
        </dd>

        <dt>Número de série</dt>
        <dd>{{ equipamento["numero_serie"] or "Não informado" }}</dd>

        <dt>Situação</dt>
        <dd>{{ equipamento["situacao"] }}</dd>
    </dl>

    {% if not bloqueado %}
        <form method="post"
                action="{{ url_for(
                    'equipamentos_excluir',
                    id_equipamento=equipamento['id_equipamento']
                ) }}">

            <input type="hidden"
                    name="_csrf_token"
                    value="{{ csrf_token() }}">

            <label class="equip-confirmacao">
                <input type="checkbox"
                        name="confirmar"
                        value="sim"
                        required>
                <span>
                    Conferi os dados e confirmo a exclusão
                    definitiva deste cadastro.
                </span>
            </label>

            <div class="equip-acoes">
                <button class="equip-botao equip-botao--perigo"
                        type="submit">
                    Confirmar exclusão definitiva
                </button>

                <a class="equip-botao equip-botao--secundario"
                    href="{{ url_for('equipamentos_lista') }}">
                    Cancelar
                </a>
            </div>
        </form>
    {% else %}
        <div class="equip-acoes">
            <a class="equip-botao equip-botao--secundario"
                href="{{ url_for('equipamentos_lista') }}">
                Voltar à lista
            </a>
        </div>
    {% endif %}
</div>

{% endblock %}
"""
)


def registrar_equipamentos(app, get_db, login_obrigatorio):
    """Registra os comandos e as rotas. Chamar uma única vez."""

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

    def criar_protecao_patrimonios(db):
        duplicados = db.execute(
            """
            SELECT
                UPPER(TRIM(patrimonio)) AS patrimonio,
                COUNT(*) AS quantidade,
                GROUP_CONCAT(id_equipamento) AS ids
            FROM equipamentos
            WHERE TRIM(patrimonio) <> ''
            GROUP BY UPPER(TRIM(patrimonio))
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        if duplicados:
            click.echo(
                "Existem patrimônios repetidos. "
                "Nenhum equipamento foi apagado:"
            )

            for item in duplicados:
                click.echo(
                    f"Patrimônio: {item['patrimonio']} | "
                    f"Quantidade: {item['quantidade']} | "
                    f"IDs: {item['ids']}"
                )

            raise click.ClickException(
                "Corrija os registros pela edição ou exclua "
                "os cadastros feitos por engano. Depois execute "
                "proteger-patrimonios novamente."
            )

        db.execute(SQL_INDICE_PATRIMONIO)

    @app.cli.command("inicializar-equipamentos")
    def inicializar_equipamentos():
        """Cria a tabela e ativa a exclusividade do patrimônio."""

        db = get_db()

        try:
            existe = db.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'unidades'
                """
            ).fetchone()

            if existe is None:
                raise click.ClickException(
                    "Inicialize o módulo de unidades primeiro."
                )

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS equipamentos (
                    id_equipamento INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_unidade INTEGER NOT NULL,
                    descricao TEXT NOT NULL,
                    patrimonio TEXT NOT NULL DEFAULT '',
                    marca TEXT NOT NULL DEFAULT '',
                    modelo TEXT NOT NULL DEFAULT '',
                    numero_serie TEXT NOT NULL DEFAULT '',
                    setor TEXT NOT NULL DEFAULT '',
                    situacao TEXT NOT NULL DEFAULT 'Não informado'
                        CHECK (
                            situacao IN (
                                'Não informado',
                                'Em uso',
                                'Em manutenção',
                                'Inativo',
                                'Baixado'
                            )
                        ),
                    referencias_os TEXT NOT NULL DEFAULT '',
                    observacoes TEXT NOT NULL DEFAULT '',
                    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_unidade)
                        REFERENCES unidades(id_unidade)
                        ON DELETE RESTRICT
                )
                """
            )

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_equipamentos_unidade
                ON equipamentos(id_unidade)
                """
            )

            criar_protecao_patrimonios(db)
            db.commit()

        except click.ClickException:
            db.rollback()
            raise

        except sqlite3.Error as erro:
            db.rollback()

            raise click.ClickException(
                f"Erro ao inicializar equipamentos: {erro}"
            ) from erro

        click.echo("Estrutura de equipamentos pronta.")
        click.echo("Proteção de patrimônios ativada.")
        click.echo("Nenhum equipamento foi importado ou apagado.")

    @app.cli.command("proteger-patrimonios")
    def proteger_patrimonios():
        """Aplica a exclusividade ao banco existente."""

        db = get_db()

        try:
            criar_protecao_patrimonios(db)
            db.commit()

        except click.ClickException:
            db.rollback()
            raise

        except sqlite3.Error as erro:
            db.rollback()

            raise click.ClickException(
                f"Erro ao proteger patrimônios: {erro}"
            ) from erro

        click.echo(
            "Proteção ativada: patrimônios preenchidos "
            "não podem se repetir."
        )

    def unidades_disponiveis(id_atual=None):
        return get_db().execute(
            """
            SELECT id_unidade, nome, ativo
            FROM unidades
            WHERE ativo = 1 OR id_unidade = ?
            ORDER BY nome COLLATE NOCASE
            """,
            (id_atual,),
        ).fetchall()

    def ler_formulario(
        id_unidade_atual=None,
        id_equipamento_atual=None,
    ):
        dados = {
            coluna: request.form.get(coluna, "").strip()
            for coluna in COLUNAS
        }

        erros = []

        if not dados["descricao"]:
            erros.append("Informe a descrição do equipamento.")

        for campo, rotulo, limite in CAMPOS:
            if len(dados[campo]) > limite:
                erros.append(
                    f"{rotulo}: use até {limite} caracteres."
                )

        if len(dados["observacoes"]) > 5000:
            erros.append(
                "As observações devem ter até 5000 caracteres."
            )

        if dados["situacao"] not in SITUACOES:
            erros.append("Selecione uma situação válida.")

        try:
            id_unidade = int(dados["id_unidade"])
        except ValueError:
            id_unidade = None

        unidade = None

        if id_unidade is not None:
            unidade = get_db().execute(
                """
                SELECT id_unidade, ativo
                FROM unidades
                WHERE id_unidade = ?
                """,
                (id_unidade,),
            ).fetchone()

            dados["id_unidade"] = str(id_unidade)

        if unidade is None:
            erros.append("Selecione uma unidade válida.")

        elif (
            not unidade["ativo"]
            and id_unidade != id_unidade_atual
        ):
            erros.append(
                "Não é permitido selecionar outra unidade "
                "que esteja inativa."
            )

        patrimonio = dados["patrimonio"]

        if patrimonio.upper() in (
            "SP",
            "SEM PATRIMÔNIO",
            "SEM PATRIMONIO",
        ):
            erros.append(
                "Se não houver número de patrimônio, "
                "deixe o campo em branco."
            )

        elif patrimonio:
            repetido = get_db().execute(
                """
                SELECT id_equipamento, descricao
                FROM equipamentos
                WHERE UPPER(TRIM(patrimonio)) = UPPER(TRIM(?))
                    AND (
                        ? IS NULL
                        OR id_equipamento <> ?
                    )
                LIMIT 1
                """,
                (
                    patrimonio,
                    id_equipamento_atual,
                    id_equipamento_atual,
                ),
            ).fetchone()

            if repetido is not None:
                erros.append(
                    f"O patrimônio {patrimonio} já pertence "
                    f"ao equipamento “{repetido['descricao']}” "
                    f"(ID {repetido['id_equipamento']}). "
                    "Informe um patrimônio exclusivo."
                )

        return dados, erros

    def mostrar_formulario(
        dados,
        erros,
        titulo,
        id_atual=None,
        id_equipamento=None,
    ):
        return render_template_string(
            FORMULARIO_HTML,
            titulo=titulo,
            dados=dados,
            erros=erros,
            campos=CAMPOS,
            situacoes=SITUACOES,
            unidades=unidades_disponiveis(id_atual),
            administrador=eh_administrador(),
            id_equipamento=id_equipamento,
        )

    def tratar_erro_gravacao(erro, erros):
        if (
            isinstance(erro, sqlite3.IntegrityError)
            and "uq_equipamentos_patrimonio_preenchido" in str(erro)
        ):
            erros.append(
                "Este patrimônio já está cadastrado em outro "
                "equipamento. Informe um patrimônio exclusivo."
            )

        elif isinstance(erro, sqlite3.IntegrityError):
            app.logger.exception(
                "Erro de integridade ao salvar equipamento"
            )

            erros.append(
                "Não foi possível salvar. Verifique a unidade "
                "e os dados informados."
            )

        else:
            app.logger.exception(
                "Erro ao salvar equipamento"
            )

            erros.append(
                "Não foi possível salvar. "
                "Confira o erro no terminal."
            )

    def identificador_sql(nome):
        # Usado somente para nomes obtidos do esquema SQLite.
        return '"' + nome.replace('"', '""') + '"'

    def possui_vinculos(db, id_equipamento):
        """
        Verifica tabelas que declaram chave estrangeira
        apontando para equipamentos.
        """

        tabelas = db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
                AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()

        for tabela in tabelas:
            nome = tabela["name"]

            chaves = db.execute(
                f"PRAGMA foreign_key_list({identificador_sql(nome)})"
            ).fetchall()

            for chave in chaves:
                if chave["table"].lower() != "equipamentos":
                    continue

                # Para relações futuras mais complexas,
                # bloqueia por segurança até revisão do módulo.
                destino = chave["to"]

                if destino not in (None, "", "id_equipamento"):
                    return True

                coluna = chave["from"]

                vinculo = db.execute(
                    f"""
                    SELECT 1
                    FROM {identificador_sql(nome)}
                    WHERE {identificador_sql(coluna)} = ?
                    LIMIT 1
                    """,
                    (id_equipamento,),
                ).fetchone()

                if vinculo is not None:
                    return True

        return False

    @app.get("/equipamentos")
    @login_obrigatorio
    def equipamentos_lista():
        db = get_db()

        busca = request.args.get("q", "").strip()[:200]
        filtro_unidade = request.args.get("id_unidade", type=int)
        filtro_situacao = request.args.get("situacao", "")
        filtro_manutencao = request.args.get("em_manutencao", "")

        if filtro_manutencao != "1":
            filtro_manutencao = ""

        if filtro_situacao not in SITUACOES:
            filtro_situacao = ""
        
        if filtro_manutencao == "1":
            condicoes.append(
                """
                (
                    e.situacao = 'Em manutenção'
                    OR EXISTS (
                        SELECT 1
                        FROM ordens_servico x
                        WHERE x.id_equipamento = e.id_equipamento
                            x.situacao = 'Em andamento'
                    )
                )
                """
            )

        condicoes = []
        parametros = []

        if busca:
            condicoes.append(
                """
                (
                    instr(lower(e.descricao), lower(?)) > 0
                    OR instr(lower(e.patrimonio), lower(?)) > 0
                    OR instr(lower(e.marca), lower(?)) > 0
                    OR instr(lower(e.modelo), lower(?)) > 0
                    OR instr(lower(e.numero_serie), lower(?)) > 0
                )
                """
            )
            parametros.extend([busca] * 5)

        if filtro_unidade is not None:
            condicoes.append("e.id_unidade = ?")
            parametros.append(filtro_unidade)

        if filtro_situacao:
            condicoes.append("e.situacao = ?")
            parametros.append(filtro_situacao)

        where = ""

        if condicoes:
            where = " WHERE " + " AND ".join(condicoes)

        total = db.execute(
            "SELECT COUNT(*) FROM equipamentos e" + where,
            parametros,
        ).fetchone()[0]

        por_pagina = 30
        paginas = max(1, (total + por_pagina - 1) // por_pagina)
        pagina = request.args.get("pagina", default=1, type=int)
        pagina = min(max(1, pagina), paginas)

        equipamentos = db.execute(
            """
            SELECT e.*, u.nome AS unidade_nome
            FROM equipamentos e
            JOIN unidades u ON u.id_unidade = e.id_unidade
            """
            + where
            + """
            ORDER BY e.descricao COLLATE NOCASE,
                        e.id_equipamento
            LIMIT ? OFFSET ?
            """,
            parametros + [
                por_pagina,
                (pagina - 1) * por_pagina,
            ],
        ).fetchall()

        unidades = db.execute(
            """
            SELECT id_unidade, nome, ativo
            FROM unidades
            ORDER BY nome COLLATE NOCASE
            """
        ).fetchall()

        return render_template_string(
            LISTA_HTML,
            equipamentos=equipamentos,
            unidades=unidades,
            situacoes=SITUACOES,
            busca=busca,
            filtro_unidade=filtro_unidade,
            filtro_situacao=filtro_situacao,
            administrador=eh_administrador(),
            total=total,
            pagina=pagina,
            paginas=paginas,
        )

    @app.route(
        "/equipamentos/novo",
        methods=["GET", "POST"],
    )
    @login_obrigatorio
    @administrador_obrigatorio
    def equipamentos_novo():
        dados = {coluna: "" for coluna in COLUNAS}
        dados["situacao"] = "Não informado"
        erros = []

        if request.method == "POST":
            dados, erros = ler_formulario()

            if not erros:
                db = get_db()

                try:
                    db.execute(
                        """
                        INSERT INTO equipamentos (
                            id_unidade, descricao, patrimonio,
                            marca, modelo, numero_serie, setor,
                            situacao, referencias_os, observacoes
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        tuple(dados[coluna] for coluna in COLUNAS),
                    )
                    db.commit()

                except sqlite3.Error as erro:
                    db.rollback()
                    tratar_erro_gravacao(erro, erros)

                else:
                    flash(
                        "Equipamento cadastrado com sucesso.",
                        "sucesso",
                    )
                    return redirect(url_for("equipamentos_lista"))

        return mostrar_formulario(
            dados,
            erros,
            "Cadastrar equipamento",
        )

    @app.route(
        "/equipamentos/<int:id_equipamento>/editar",
        methods=["GET", "POST"],
    )
    @login_obrigatorio
    def equipamentos_editar(id_equipamento):
        db = get_db()

        equipamento = db.execute(
            """
            SELECT *
            FROM equipamentos
            WHERE id_equipamento = ?
            """,
            (id_equipamento,),
        ).fetchone()

        if equipamento is None:
            abort(404)

        if request.method == "POST" and not eh_administrador():
            abort(403)

        dados = {
            coluna: (
                ""
                if equipamento[coluna] is None
                else str(equipamento[coluna])
            )
            for coluna in COLUNAS
        }
        erros = []

        if request.method == "POST":
            dados, erros = ler_formulario(
                id_unidade_atual=equipamento["id_unidade"],
                id_equipamento_atual=id_equipamento,
            )

            if not erros:
                try:
                    db.execute(
                        """
                        UPDATE equipamentos
                        SET id_unidade = ?,
                            descricao = ?,
                            patrimonio = ?,
                            marca = ?,
                            modelo = ?,
                            numero_serie = ?,
                            setor = ?,
                            situacao = ?,
                            referencias_os = ?,
                            observacoes = ?,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id_equipamento = ?
                        """,
                        tuple(
                            dados[coluna] for coluna in COLUNAS
                        ) + (id_equipamento,),
                    )
                    db.commit()

                except sqlite3.Error as erro:
                    db.rollback()
                    tratar_erro_gravacao(erro, erros)

                else:
                    flash(
                        "Equipamento atualizado com sucesso.",
                        "sucesso",
                    )
                    return redirect(url_for("equipamentos_lista"))

        titulo = (
            "Editar equipamento"
            if eh_administrador()
            else "Visualizar equipamento"
        )

        return mostrar_formulario(
            dados,
            erros,
            titulo,
            id_atual=equipamento["id_unidade"],
            id_equipamento=id_equipamento,
        )

    @app.route(
        "/equipamentos/<int:id_equipamento>/excluir",
        methods=["GET", "POST"],
    )
    @login_obrigatorio
    @administrador_obrigatorio
    def equipamentos_excluir(id_equipamento):
        db = get_db()
        erro = None
        bloqueado = False

        def buscar_equipamento():
            return db.execute(
                """
                SELECT e.*, u.nome AS unidade_nome
                FROM equipamentos e
                JOIN unidades u ON u.id_unidade = e.id_unidade
                WHERE e.id_equipamento = ?
                """,
                (id_equipamento,),
            ).fetchone()

        equipamento = buscar_equipamento()

        if equipamento is None:
            abort(404)

        if request.method == "POST":
            if request.form.get("confirmar") != "sim":
                erro = (
                    "Marque a confirmação para excluir "
                    "definitivamente este cadastro."
                )

            else:
                try:
                    # Mantém a verificação dos vínculos e a exclusão
                    # na mesma transação de escrita.
                    db.execute("BEGIN IMMEDIATE")

                    equipamento = buscar_equipamento()

                    if equipamento is None:
                        db.rollback()
                        abort(404)

                    if possui_vinculos(db, id_equipamento):
                        db.rollback()
                        bloqueado = True
                        erro = (
                            "Exclusão bloqueada: existem registros "
                            "vinculados a este equipamento. "
                            "Preserve o histórico e use Inativo "
                            "ou Baixado quando apropriado."
                        )

                    else:
                        db.execute(
                            """
                            DELETE FROM equipamentos
                            WHERE id_equipamento = ?
                            """,
                            (id_equipamento,),
                        )
                        db.commit()

                        flash(
                            f"Cadastro ID {id_equipamento} "
                            "excluído com sucesso.",
                            "sucesso",
                        )
                        return redirect(
                            url_for("equipamentos_lista")
                        )

                except sqlite3.IntegrityError:
                    db.rollback()
                    bloqueado = True
                    erro = (
                        "Exclusão bloqueada por vínculo "
                        "com outros registros."
                    )

                except sqlite3.Error:
                    db.rollback()
                    app.logger.exception(
                        "Erro ao excluir equipamento"
                    )
                    erro = (
                        "Não foi possível excluir. "
                        "Confira o erro no terminal."
                    )

        else:
            bloqueado = possui_vinculos(db, id_equipamento)

            if bloqueado:
                erro = (
                    "Este equipamento possui registros vinculados "
                    "e não pode ser excluído. Preserve o histórico "
                    "e use Inativo ou Baixado quando apropriado."
                )

        return render_template_string(
            EXCLUIR_HTML,
            equipamento=equipamento,
            erro=erro,
            bloqueado=bloqueado,
        )