import sqlite3
from datetime import date
from functools import wraps

from flask import (
    abort,
    flash,
    g,
    redirect,
    render_template_string,
    request,
    url_for,
)


CAMPOS_TEXTO_OS = (
    ("descricao_equipamento", "Descrição do equipamento no documento", 300),
    ("patrimonio_informado", "Patrimônio informado no documento", 80),
    ("empresa_responsavel", "Empresa responsável", 200),
    ("tecnico_responsavel", "Técnico / responsável pelo atendimento", 200),
)


CAMPOS_LONGOS_OS = (
    ("problema_relatado", "Problema relatado"),
    ("servico_realizado", "Serviço realizado"),
    ("observacoes", "Observações"),
)


COLUNAS_OS = (
    "numero_os",
    "id_unidade",
    "id_equipamento",
    "descricao_equipamento",
    "patrimonio_informado",
    "tipo_manutencao",
    "modalidade",
    "empresa_responsavel",
    "tecnico_responsavel",
    "data_abertura",
    "data_conclusao",
    "situacao",
    "problema_relatado",
    "servico_realizado",
    "observacoes",
)


ESTILO_OS = """
<style>
    .os-acoes,
    .os-paginacao {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 12px;
        margin: 18px 0;
    }

    .os-botao {
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

    .os-botao--secundario {
        background: #475569;
    }

    .os-grade {
        display: grid;
        grid-template-columns: repeat(
            auto-fit, minmax(240px, 1fr)
        );
        gap: 18px;
    }

    .os-campo label {
        display: block;
        margin-bottom: 6px;
        font-weight: 600;
    }

    .os-campo input,
    .os-campo select,
    .os-campo textarea {
        width: 100%;
        padding: 11px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: white;
        color: #1e293b;
        font: inherit;
        box-sizing: border-box;
    }

    .os-campo small,
    .os-tabela small {
        display: block;
        margin-top: 6px;
        color: #475569;
    }

    .os-campo--inteiro {
        grid-column: 1 / -1;
    }

    .os-tabela-container {
        overflow-x: auto;
    }

    .os-tabela {
        width: 100%;
        border-collapse: collapse;
    }

    .os-tabela th,
    .os-tabela td {
        padding: 12px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
        vertical-align: top;
    }

    .os-tabela th {
        background: #f1f5f9;
    }

    .os-erros {
        padding: 16px 32px;
        border-radius: 6px;
        background: #fee2e2;
        color: #991b1b;
    }

    .os-ajuda {
        padding: 16px;
        margin-bottom: 18px;
        border-radius: 6px;
        background: #e0f2fe;
        color: #0c4a6e;
    }
</style>
"""


LISTA_OS_HTML = (
    """
{% extends "base.html" %}

{% block title %}
    Ordens de serviço | Gestão de Equipamentos Clínicos
{% endblock %}

{% block extra_head %}
"""
    + ESTILO_OS
    + """
{% endblock %}

{% block content %}
<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">MANUTENÇÃO</p>
        <h1>Ordens de serviço</h1>

        <p class="descricao">
            Registre os atendimentos por unidade e vincule
            o equipamento quando seu cadastro estiver disponível.
        </p>
    </div>
</section>

<div class="os-acoes">
    <span>{{ total }} OS encontrada(s)</span>

    {% if administrador %}
        <a class="os-botao"
           href="{{ url_for('ordens_nova') }}">
            Cadastrar OS
        </a>
    {% endif %}
</div>

<form method="get"
      action="{{ url_for('ordens_lista') }}"
      class="painel">

    <div class="os-grade">
        <div class="os-campo">
            <label for="q">Pesquisar</label>

            <input id="q" name="q"
                   value="{{ busca }}"
                   maxlength="200"
                   placeholder="Número, equipamento, patrimônio ou empresa">
        </div>

        <div class="os-campo">
            <label for="id_unidade">Unidade do atendimento</label>

            <select id="id_unidade" name="id_unidade">
                <option value="">Todas</option>

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

        <div class="os-campo">
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

        <div class="os-campo">
            <label for="tipo_manutencao">Tipo de manutenção</label>

            <select id="tipo_manutencao" name="tipo_manutencao">
                <option value="">Todos</option>

                {% for item in tipos %}
                    <option value="{{ item }}"
                        {% if filtro_tipo == item %}
                            selected
                        {% endif %}>
                        {{ item }}
                    </option>
                {% endfor %}
            </select>
        </div>

        <div class="os-campo">
            <label for="vinculo">Vínculo com equipamento</label>

            <select id="vinculo" name="vinculo">
                <option value="">Todos</option>

                <option value="sem"
                    {% if filtro_vinculo == "sem" %}
                        selected
                    {% endif %}>
                    Sem equipamento vinculado
                </option>

                <option value="com"
                    {% if filtro_vinculo == "com" %}
                        selected
                    {% endif %}>
                    Com equipamento vinculado
                </option>
            </select>
        </div>
    </div>

    <div class="os-acoes">
        <button class="os-botao" type="submit">
            Filtrar
        </button>

        <a href="{{ url_for('ordens_lista') }}">
            Limpar
        </a>
    </div>
</form>

<div class="painel os-tabela-container">
    <table class="os-tabela">
        <thead>
            <tr>
                <th scope="col">OS</th>
                <th scope="col">Unidade do atendimento</th>
                <th scope="col">Equipamento</th>
                <th scope="col">Manutenção</th>
                <th scope="col">Situação</th>
                <th scope="col">Ação</th>
            </tr>
        </thead>

        <tbody>
            {% for os in ordens %}
                <tr>
                    <td>
                        {{ os["numero_os"] or "Sem número" }}

                        <small>ID: {{ os["id_os"] }}</small>

                        <small>
                            Atendimento:
                            {{ formatar_data(os["data_abertura"]) }}
                        </small>

                        {% if os["data_conclusao"] %}
                            <small>
                                Conclusão:
                                {{ formatar_data(os["data_conclusao"]) }}
                            </small>
                        {% endif %}
                    </td>

                    <td>
                        {{ os["unidade_nome"] }}
                    </td>

                    <td>
                        {% if os["id_equipamento"] is not none %}
                            {{ os["equipamento_nome"] }}

                            <small>
                                Patrimônio atual:
                                {{ os["equipamento_patrimonio"] or "Não informado" }}
                            </small>

                            <small>Equipamento vinculado</small>
                        {% else %}
                            {{ os["descricao_equipamento"] or "Não descrito" }}

                            <small>
                                Patrimônio no documento:
                                {{ os["patrimonio_informado"] or "Não informado" }}
                            </small>

                            <small>Vínculo pendente</small>
                        {% endif %}
                    </td>

                    <td>
                        {{ os["tipo_manutencao"] }}

                        <small>{{ os["modalidade"] }}</small>

                        <small>
                            {{ os["empresa_responsavel"] or "Empresa não informada" }}
                        </small>
                    </td>

                    <td>{{ os["situacao"] }}</td>

                    <td>
                        <div class="os-acoes">
                            <a href="{{ url_for(
                                'ordens_editar',
                                id_os=os['id_os']
                            ) }}">
                                {{ "Editar / vincular" if administrador else "Visualizar" }}
                            </a>

                            <a href="{{ url_for(
                                'ordens_anexos',
                                id_os=os['id_os']
                            ) }}">
                                PDFs
                            </a>
                        </div>
                    </td>
                </tr>
            {% else %}
                <tr>
                    <td colspan="6">
                        Nenhuma ordem de serviço encontrada.
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<nav class="os-paginacao" aria-label="Paginação">
    {% if pagina > 1 %}
        <a href="{{ url_for(
            'ordens_lista',
            q=busca,
            id_unidade=filtro_unidade or '',
            situacao=filtro_situacao,
            tipo_manutencao=filtro_tipo,
            vinculo=filtro_vinculo,
            pagina=pagina-1
        ) }}">
            Anterior
        </a>
    {% endif %}

    <span>Página {{ pagina }} de {{ paginas }}</span>

    {% if pagina < paginas %}
        <a href="{{ url_for(
            'ordens_lista',
            q=busca,
            id_unidade=filtro_unidade or '',
            situacao=filtro_situacao,
            tipo_manutencao=filtro_tipo,
            vinculo=filtro_vinculo,
            pagina=pagina+1
        ) }}">
            Próxima
        </a>
    {% endif %}
</nav>
{% endblock %}
"""
)


FORMULARIO_OS_HTML = (
    """
{% extends "base.html" %}

{% block title %}
    {{ titulo }} | Gestão de Equipamentos Clínicos
{% endblock %}

{% block extra_head %}
"""
    + ESTILO_OS
    + """
{% endblock %}

{% block content %}
<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">MANUTENÇÃO</p>
        <h1>{{ titulo }}</h1>
        <p class="descricao">
            Só a unidade do atendimento (*) é obrigatória.
            Os detalhes estão no PDF original, que você anexa
            depois de salvar.
        </p>
    </div>
</section>

{% if erros %}
    <ul class="os-erros" role="alert">
        {% for erro in erros %}
            <li>{{ erro }}</li>
        {% endfor %}
    </ul>
{% endif %}

<div class="os-ajuda">
    Você pode salvar a OS sem equipamento cadastrado.
    Informe a unidade do atendimento e, se disponíveis,
    a descrição e o patrimônio escritos no documento.
    Depois, edite a OS para vincular o equipamento.
    O vínculo não altera os dados da ficha do equipamento.
</div>

<form method="post" class="painel">
    <input type="hidden"
           name="_csrf_token"
           value="{{ csrf_token() }}">

    <fieldset {% if not administrador %}disabled{% endif %}
              style="border:0; padding:0; min-width:0;">

        <div class="os-grade">
            <div class="os-campo">
                <label for="numero_os">Número da OS</label>

                <input id="numero_os" name="numero_os"
                       value="{{ dados['numero_os'] }}"
                       maxlength="100">

                <small>
                    Deixe em branco se não constar no documento.
                    O sistema mantém um ID interno.
                </small>
            </div>

            <div class="os-campo">
                <label for="id_unidade">Unidade do atendimento *</label>

                <select id="id_unidade" name="id_unidade" required>
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

                <small>
                    Local do atendimento. Não acompanha
                    automaticamente futuras transferências.
                </small>
            </div>

            <div class="os-campo os-campo--inteiro">
                <label for="id_equipamento">
                    Equipamento cadastrado — opcional
                </label>

                <select id="id_equipamento" name="id_equipamento">
                    <option value="">
                        Ainda não vinculado / não cadastrado
                    </option>

                    {% for equipamento in equipamentos %}
                        <option value="{{ equipamento['id_equipamento'] }}"
                            {% if dados['id_equipamento'] == (equipamento['id_equipamento']|string) %}
                                selected
                            {% endif %}>
                            {{ equipamento["descricao"] }}
                            — Patrimônio:
                            {{ equipamento["patrimonio"] or "Não informado" }}
                            — Unidade atual:
                            {{ equipamento["unidade_nome"] }}
                            — ID {{ equipamento["id_equipamento"] }}
                        </option>
                    {% endfor %}
                </select>

                <small>
                    Confira a identidade do aparelho.
                    Sua unidade atual pode ser diferente da unidade
                    de um atendimento antigo.
                </small>
            </div>

            {% for campo, rotulo, limite in campos_texto %}
                <div class="os-campo">
                    <label for="{{ campo }}">{{ rotulo }}</label>

                    <input id="{{ campo }}" name="{{ campo }}"
                           value="{{ dados[campo] }}"
                           maxlength="{{ limite }}">
                </div>
            {% endfor %}

            <div class="os-campo">
                <label for="tipo_manutencao">Tipo de manutenção</label>

                <select id="tipo_manutencao" name="tipo_manutencao">
                    {% for item in tipos %}
                        <option value="{{ item }}"
                            {% if dados['tipo_manutencao'] == item %}
                                selected
                            {% endif %}>
                            {{ item }}
                        </option>
                    {% endfor %}
                </select>
            </div>

            <div class="os-campo">
                <label for="modalidade">Modalidade</label>

                <select id="modalidade" name="modalidade">
                    {% for item in modalidades %}
                        <option value="{{ item }}"
                            {% if dados['modalidade'] == item %}
                                selected
                            {% endif %}>
                            {{ item }}
                        </option>
                    {% endfor %}
                </select>
            </div>

            <div class="os-campo">
                <label for="data_abertura">Data do atendimento</label>

                <input id="data_abertura" name="data_abertura"
                       type="date"
                       value="{{ dados['data_abertura'] }}">

                <small>Deixe em branco se não souber.</small>
            </div>

            <div class="os-campo">
                <label for="data_conclusao">Data de conclusão</label>

                <input id="data_conclusao" name="data_conclusao"
                       type="date"
                       value="{{ dados['data_conclusao'] }}">

                <small>Opcional.</small>
            </div>

            <div class="os-campo">
                <label for="situacao">Situação</label>

                <select id="situacao" name="situacao">
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

            {% for campo, rotulo in campos_longos %}
                <div class="os-campo os-campo--inteiro">
                    <label for="{{ campo }}">{{ rotulo }}</label>

                    <textarea id="{{ campo }}" name="{{ campo }}"
                              rows="4" maxlength="10000"
                    >{{ dados[campo] }}</textarea>
                </div>
            {% endfor %}
        </div>
    </fieldset>

    <div class="os-acoes">
        {% if administrador %}
            <button class="os-botao" type="submit"
                    name="acao" value="salvar">
                Salvar ordem de serviço
            </button>

            <button class="os-botao" type="submit"
                    name="acao" value="salvar_e_anexar">
                Salvar e anexar PDF
            </button>
        {% endif %}

        <a class="os-botao os-botao--secundario"
           href="{{ url_for('ordens_lista') }}">
            Voltar à lista
        </a>
    </div>
</form>

<div class="os-ajuda">
    Use "Salvar e anexar PDF" para enviar o documento original
    logo após salvar. Salvar ou concluir esta OS não altera
    automaticamente a situação do equipamento.
</div>
{% endblock %}
"""
)


def registrar_telas_os(
    app,
    get_db,
    login_obrigatorio,
    situacoes,
    tipos,
    modalidades,
):
    """Registra listagem, cadastro e edição de OS."""

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

    def formatar_data(valor):
        if not valor:
            return "Não informada"

        try:
            return date.fromisoformat(valor).strftime("%d/%m/%Y")
        except ValueError:
            return valor

    def buscar_unidades():
        return get_db().execute(
            """
            SELECT id_unidade, nome, ativo
            FROM unidades
            ORDER BY nome COLLATE NOCASE
            """
        ).fetchall()

    def buscar_equipamentos():
        return get_db().execute(
            """
            SELECT
                e.id_equipamento,
                e.descricao,
                e.patrimonio,
                u.nome AS unidade_nome
            FROM equipamentos e
            JOIN unidades u ON u.id_unidade = e.id_unidade
            ORDER BY e.descricao COLLATE NOCASE,
                     e.id_equipamento
            """
        ).fetchall()

    def ler_formulario():
        dados = {
            coluna: request.form.get(coluna, "").strip()
            for coluna in COLUNAS_OS
        }

        erros = []
        db = get_db()

        if len(dados["numero_os"]) > 100:
            erros.append("O número da OS deve ter até 100 caracteres.")

        for campo, rotulo, limite in CAMPOS_TEXTO_OS:
            if len(dados[campo]) > limite:
                erros.append(
                    f"{rotulo}: use até {limite} caracteres."
                )

        for campo, rotulo in CAMPOS_LONGOS_OS:
            if len(dados[campo]) > 10000:
                erros.append(
                    f"{rotulo}: use até 10000 caracteres."
                )

        try:
            id_unidade = int(dados["id_unidade"])
        except ValueError:
            id_unidade = None

        unidade = None

        if id_unidade is not None:
            unidade = db.execute(
                "SELECT id_unidade FROM unidades WHERE id_unidade = ?",
                (id_unidade,),
            ).fetchone()

            dados["id_unidade"] = str(id_unidade)

        if unidade is None:
            erros.append("Selecione uma unidade válida.")

        if dados["id_equipamento"]:
            try:
                id_equipamento = int(dados["id_equipamento"])
            except ValueError:
                id_equipamento = None

            equipamento = None

            if id_equipamento is not None:
                equipamento = db.execute(
                    """
                    SELECT id_equipamento
                    FROM equipamentos
                    WHERE id_equipamento = ?
                    """,
                    (id_equipamento,),
                ).fetchone()

                dados["id_equipamento"] = str(id_equipamento)

            if equipamento is None:
                erros.append(
                    "Selecione um equipamento válido "
                    "ou deixe sem vínculo."
                )

        if dados["situacao"] not in situacoes:
            erros.append("Selecione uma situação válida.")

        if dados["tipo_manutencao"] not in tipos:
            erros.append("Selecione um tipo de manutenção válido.")

        if dados["modalidade"] not in modalidades:
            erros.append("Selecione uma modalidade válida.")

        abertura = None
        conclusao = None

        if dados["data_abertura"]:
            try:
                abertura = date.fromisoformat(dados["data_abertura"])
                dados["data_abertura"] = abertura.isoformat()
            except ValueError:
                erros.append("Informe uma data do atendimento válida.")

        if dados["data_conclusao"]:
            try:
                conclusao = date.fromisoformat(dados["data_conclusao"])
                dados["data_conclusao"] = conclusao.isoformat()
            except ValueError:
                erros.append("Informe uma data de conclusão válida.")

        if abertura and conclusao and conclusao < abertura:
            erros.append(
                "A data de conclusão não pode ser anterior "
                "à data do atendimento."
            )

        return dados, erros

    def valores_para_banco(dados):
        valores = dict(dados)

        valores["id_unidade"] = int(valores["id_unidade"])

        valores["id_equipamento"] = (
            int(valores["id_equipamento"])
            if valores["id_equipamento"]
            else None
        )

        valores["data_conclusao"] = (
            valores["data_conclusao"] or None
        )

        return tuple(valores[coluna] for coluna in COLUNAS_OS)

    def mostrar_formulario(dados, erros, titulo):
        return render_template_string(
            FORMULARIO_OS_HTML,
            titulo=titulo,
            dados=dados,
            erros=erros,
            unidades=buscar_unidades(),
            equipamentos=buscar_equipamentos(),
            campos_texto=CAMPOS_TEXTO_OS,
            campos_longos=CAMPOS_LONGOS_OS,
            situacoes=situacoes,
            tipos=tipos,
            modalidades=modalidades,
            administrador=eh_administrador(),
        )

    @app.get("/ordens-servico")
    @login_obrigatorio
    def ordens_lista():
        db = get_db()

        busca = request.args.get("q", "").strip()[:200]
        filtro_unidade = request.args.get("id_unidade", type=int)
        filtro_situacao = request.args.get("situacao", "")
        filtro_tipo = request.args.get("tipo_manutencao", "")
        filtro_vinculo = request.args.get("vinculo", "")

        if filtro_situacao not in situacoes:
            filtro_situacao = ""

        if filtro_tipo not in tipos:
            filtro_tipo = ""

        if filtro_vinculo not in ("sem", "com"):
            filtro_vinculo = ""

        condicoes = []
        parametros = []

        if busca:
            condicoes.append(
                """
                (
                    instr(lower(o.numero_os), lower(?)) > 0
                    OR instr(lower(o.descricao_equipamento), lower(?)) > 0
                    OR instr(lower(o.patrimonio_informado), lower(?)) > 0
                    OR instr(lower(o.empresa_responsavel), lower(?)) > 0
                    OR instr(lower(COALESCE(e.descricao, '')), lower(?)) > 0
                    OR instr(lower(COALESCE(e.patrimonio, '')), lower(?)) > 0
                )
                """
            )
            parametros.extend([busca] * 6)

        if filtro_unidade is not None:
            condicoes.append("o.id_unidade = ?")
            parametros.append(filtro_unidade)

        if filtro_situacao:
            condicoes.append("o.situacao = ?")
            parametros.append(filtro_situacao)

        if filtro_tipo:
            condicoes.append("o.tipo_manutencao = ?")
            parametros.append(filtro_tipo)

        if filtro_vinculo == "sem":
            condicoes.append("o.id_equipamento IS NULL")

        elif filtro_vinculo == "com":
            condicoes.append("o.id_equipamento IS NOT NULL")

        where = ""

        if condicoes:
            where = " WHERE " + " AND ".join(condicoes)

        origem = """
            FROM ordens_servico o
            JOIN unidades u ON u.id_unidade = o.id_unidade
            LEFT JOIN equipamentos e
                ON e.id_equipamento = o.id_equipamento
        """

        total = db.execute(
            "SELECT COUNT(*) " + origem + where,
            parametros,
        ).fetchone()[0]

        por_pagina = 30
        paginas = max(1, (total + por_pagina - 1) // por_pagina)
        pagina = request.args.get("pagina", default=1, type=int)
        pagina = min(max(1, pagina), paginas)

        ordens = db.execute(
            """
            SELECT
                o.*,
                u.nome AS unidade_nome,
                e.descricao AS equipamento_nome,
                e.patrimonio AS equipamento_patrimonio
            """
            + origem
            + where
            + """
            ORDER BY o.data_abertura DESC, o.id_os DESC
            LIMIT ? OFFSET ?
            """,
            parametros + [
                por_pagina,
                (pagina - 1) * por_pagina,
            ],
        ).fetchall()

        return render_template_string(
            LISTA_OS_HTML,
            ordens=ordens,
            unidades=buscar_unidades(),
            situacoes=situacoes,
            tipos=tipos,
            busca=busca,
            filtro_unidade=filtro_unidade,
            filtro_situacao=filtro_situacao,
            filtro_tipo=filtro_tipo,
            filtro_vinculo=filtro_vinculo,
            total=total,
            pagina=pagina,
            paginas=paginas,
            administrador=eh_administrador(),
            formatar_data=formatar_data,
        )

    @app.route(
        "/ordens-servico/nova",
        methods=["GET", "POST"],
    )
    @login_obrigatorio
    @administrador_obrigatorio
    def ordens_nova():
        dados = {coluna: "" for coluna in COLUNAS_OS}

        dados.update(
            situacao="Não informada",
            tipo_manutencao="Não informado",
            modalidade="Não informada",
            data_abertura="",
        )

        erros = []

        if request.method == "POST":
            dados, erros = ler_formulario()

            if not erros:
                db = get_db()
                id_usuario = g.usuario["id_usuario"]

                duplicada = bool(dados["numero_os"]) and (
                    db.execute(
                        """
                        SELECT 1
                        FROM ordens_servico
                        WHERE numero_os = ?
                        LIMIT 1
                        """,
                        (dados["numero_os"],),
                    ).fetchone()
                    is not None
                )

                try:
                    cursor = db.execute(
                        """
                        INSERT INTO ordens_servico (
                            numero_os,
                            id_unidade,
                            id_equipamento,
                            descricao_equipamento,
                            patrimonio_informado,
                            tipo_manutencao,
                            modalidade,
                            empresa_responsavel,
                            tecnico_responsavel,
                            data_abertura,
                            data_conclusao,
                            situacao,
                            problema_relatado,
                            servico_realizado,
                            observacoes,
                            criado_por,
                            atualizado_por
                        )
                        VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?
                        )
                        """,
                        valores_para_banco(dados)
                        + (id_usuario, id_usuario),
                    )

                    id_nova = cursor.lastrowid

                    db.commit()

                except sqlite3.Error:
                    db.rollback()
                    app.logger.exception("Erro ao cadastrar OS")

                    erros.append(
                        "Não foi possível salvar a OS. "
                        "Confira o erro no terminal."
                    )

                else:
                    mensagem = "Ordem de serviço cadastrada com sucesso."

                    if duplicada:
                        mensagem += (
                            " Atenção: já existe outra OS com "
                            "este número. Confira se não é duplicidade."
                        )

                    flash(mensagem, "sucesso")

                    if request.form.get("acao") == "salvar_e_anexar":
                        return redirect(
                            url_for("ordens_anexos", id_os=id_nova)
                        )

                    return redirect(url_for("ordens_lista"))

        return mostrar_formulario(
            dados,
            erros,
            "Cadastrar ordem de serviço",
        )

    @app.route(
        "/ordens-servico/<int:id_os>/editar",
        methods=["GET", "POST"],
    )
    @login_obrigatorio
    def ordens_editar(id_os):
        db = get_db()

        ordem = db.execute(
            "SELECT * FROM ordens_servico WHERE id_os = ?",
            (id_os,),
        ).fetchone()

        if ordem is None:
            abort(404)

        if request.method == "POST" and not eh_administrador():
            abort(403)

        dados = {
            coluna: (
                ""
                if ordem[coluna] is None
                else str(ordem[coluna])
            )
            for coluna in COLUNAS_OS
        }

        erros = []

        if request.method == "POST":
            dados, erros = ler_formulario()

            if not erros:
                try:
                    db.execute(
                        """
                        UPDATE ordens_servico
                        SET numero_os = ?,
                            id_unidade = ?,
                            id_equipamento = ?,
                            descricao_equipamento = ?,
                            patrimonio_informado = ?,
                            tipo_manutencao = ?,
                            modalidade = ?,
                            empresa_responsavel = ?,
                            tecnico_responsavel = ?,
                            data_abertura = ?,
                            data_conclusao = ?,
                            situacao = ?,
                            problema_relatado = ?,
                            servico_realizado = ?,
                            observacoes = ?,
                            atualizado_por = ?,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id_os = ?
                        """,
                        valores_para_banco(dados)
                        + (g.usuario["id_usuario"], id_os),
                    )

                    db.commit()

                except sqlite3.Error:
                    db.rollback()
                    app.logger.exception("Erro ao editar OS")

                    erros.append(
                        "Não foi possível atualizar a OS. "
                        "Confira o erro no terminal."
                    )

                else:
                    flash(
                        "Ordem de serviço atualizada com sucesso.",
                        "sucesso",
                    )

                    if request.form.get("acao") == "salvar_e_anexar":
                        return redirect(
                            url_for("ordens_anexos", id_os=id_os)
                        )

                    return redirect(url_for("ordens_lista"))

        titulo = (
            "Editar ordem de serviço"
            if eh_administrador()
            else "Visualizar ordem de serviço"
        )

        return mostrar_formulario(dados, erros, titulo)