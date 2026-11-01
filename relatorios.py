from datetime import date
from io import BytesIO

from flask import (
    abort,
    g,
    render_template_string,
    request,
    send_file,
    url_for,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ESTILO = """
<style>
    .rel-acoes {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        margin: 18px 0;
    }

    .rel-botao {
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

    .rel-botao--secundario {
        background: #475569;
    }

    .rel-grade {
        display: grid;
        grid-template-columns: repeat(
            auto-fit, minmax(220px, 1fr)
        );
        gap: 18px;
    }

    .rel-campo label {
        display: block;
        margin-bottom: 6px;
        font-weight: 600;
    }

    .rel-campo input,
    .rel-campo select {
        width: 100%;
        padding: 11px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: white;
        color: #1e293b;
        font: inherit;
        box-sizing: border-box;
    }

    .rel-tabela-container {
        overflow-x: auto;
    }

    .rel-tabela {
        width: 100%;
        border-collapse: collapse;
    }

    .rel-tabela th,
    .rel-tabela td {
        padding: 12px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
        vertical-align: top;
    }

    .rel-tabela th {
        background: #f1f5f9;
    }

    .rel-ajuda {
        padding: 16px;
        margin: 18px 0;
        border-radius: 6px;
        background: #e0f2fe;
        color: #0c4a6e;
    }
</style>
"""


PAGINA_HTML = (
    """
{% extends "base.html" %}

{% block title %}
    Relatórios | Gestão de Equipamentos Clínicos
{% endblock %}

{% block extra_head %}
"""
    + ESTILO
    + """
{% endblock %}

{% block content %}
<section class="cabecalho-pagina">
    <div>
        <p class="sobretitulo">CONSULTAS E DOCUMENTOS</p>
        <h1>Relatórios</h1>

        <p class="descricao">
            Consulte unidades, equipamentos e ordens de serviço,
            separadamente ou vinculados, e gere o PDF do relatório.
        </p>
    </div>
</section>

<form method="get"
      action="{{ url_for('relatorios') }}"
      class="painel">

    <div class="rel-grade">
        <div class="rel-campo">
            <label for="tipo">Relatório</label>

            <select id="tipo" name="tipo">
                {% for valor, rotulo in tipos %}
                    <option value="{{ valor }}"
                        {% if tipo == valor %}selected{% endif %}>
                        {{ rotulo }}
                    </option>
                {% endfor %}
            </select>
        </div>

        <div class="rel-campo">
            <label for="id_unidade">Unidade</label>

            <select id="id_unidade" name="id_unidade">
                <option value="">Todas</option>

                {% for unidade in unidades %}
                    <option value="{{ unidade['id_unidade'] }}"
                        {% if filtro_unidade == unidade['id_unidade'] %}
                            selected
                        {% endif %}>
                        {{ unidade["nome"] }}
                    </option>
                {% endfor %}
            </select>
        </div>

        <div class="rel-campo">
            <label for="id_equipamento">Equipamento</label>

            <select id="id_equipamento" name="id_equipamento">
                <option value="">Todos</option>

                {% for equipamento in equipamentos %}
                    <option value="{{ equipamento['id_equipamento'] }}"
                        {% if filtro_equipamento == equipamento['id_equipamento'] %}
                            selected
                        {% endif %}>
                        {{ equipamento["descricao"] }}
                        — {{ equipamento["patrimonio"] or "sem patrimônio" }}
                    </option>
                {% endfor %}
            </select>
        </div>

        <div class="rel-campo">
            <label for="data_inicio">Data inicial do atendimento</label>

            <input id="data_inicio" name="data_inicio"
                   type="date"
                   value="{{ data_inicio }}">
        </div>

        <div class="rel-campo">
            <label for="data_fim">Data final do atendimento</label>

            <input id="data_fim" name="data_fim"
                   type="date"
                   value="{{ data_fim }}">
        </div>
    </div>

    <div class="rel-acoes">
        <button class="rel-botao" type="submit">
            Consultar
        </button>

        <a class="rel-botao rel-botao--secundario"
           href="{{ url_for('relatorios') }}">
            Limpar
        </a>
    </div>
</form>

<div class="rel-ajuda">
    Os filtros de unidade, equipamento e data se aplicam
    quando fizer sentido para o relatório escolhido.
    Dados não informados aparecem como “Não informado”.
</div>

<div class="rel-acoes">
    <a class="rel-botao"
       href="{{ url_for(
           'relatorios_pdf',
           tipo=tipo,
           id_unidade=filtro_unidade or '',
           id_equipamento=filtro_equipamento or '',
           data_inicio=data_inicio,
           data_fim=data_fim
       ) }}">
        Gerar PDF deste relatório
    </a>
</div>

<div class="painel rel-tabela-container">
    <h2>{{ titulo }}</h2>

    <table class="rel-tabela">
        <thead>
            <tr>
                {% for coluna in colunas %}
                    <th scope="col">{{ coluna }}</th>
                {% endfor %}
            </tr>
        </thead>

        <tbody>
            {% for linha in linhas %}
                <tr>
                    {% for valor in linha %}
                        <td>{{ valor }}</td>
                    {% endfor %}
                </tr>
            {% else %}
                <tr>
                    <td colspan="{{ colunas|length }}">
                        Nenhum registro encontrado para os filtros escolhidos.
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""
)


def registrar_relatorios(app, get_db, login_obrigatorio):
    """Registra a seção de relatórios e a geração de PDF."""

    tipos = (
        ("unidades", "Unidades"),
        ("equipamentos", "Equipamentos"),
        ("ordens", "Ordens de serviço"),
        ("os_unidade", "OS por unidade"),
        ("historico_equipamento", "Histórico do equipamento"),
        ("os_sem_equipamento", "OS sem equipamento vinculado"),
        ("inventario_unidade", "Inventário por unidade"),
    )

    rotulos = dict(tipos)

    def eh_administrador():
        return (
            g.usuario is not None
            and g.usuario["papel"] == "administrador_principal"
        )

    def formatar_data(valor):
        if not valor:
            return "Não informado"

        try:
            return date.fromisoformat(
                str(valor)[:10]
            ).strftime("%d/%m/%Y")
        except ValueError:
            return valor

    def ler_filtros():
        tipo = request.args.get("tipo", "unidades")

        if tipo not in rotulos:
            tipo = "unidades"

        filtro_unidade = request.args.get("id_unidade", type=int)
        filtro_equipamento = request.args.get(
            "id_equipamento", type=int
        )
        data_inicio = request.args.get("data_inicio", "").strip()
        data_fim = request.args.get("data_fim", "").strip()

        return (
            tipo,
            filtro_unidade,
            filtro_equipamento,
            data_inicio,
            data_fim,
        )

    def montar_consulta(
        tipo,
        filtro_unidade,
        filtro_equipamento,
        data_inicio,
        data_fim,
    ):
        condicoes = []
        parametros = []

        if tipo in ("ordens", "os_unidade", "os_sem_equipamento"):
            if filtro_unidade is not None:
                condicoes.append("o.id_unidade = ?")
                parametros.append(filtro_unidade)

            if filtro_equipamento is not None:
                condicoes.append("o.id_equipamento = ?")
                parametros.append(filtro_equipamento)

            if data_inicio:
                condicoes.append(
                    "o.data_abertura >= ?"
                )
                parametros.append(data_inicio)

            if data_fim:
                condicoes.append(
                    "o.data_abertura <= ?"
                )
                parametros.append(data_fim)

            if tipo == "os_sem_equipamento":
                condicoes.append("o.id_equipamento IS NULL")

        if tipo in ("equipamentos", "historico_equipamento"):
            if filtro_unidade is not None:
                condicoes.append("e.id_unidade = ?")
                parametros.append(filtro_unidade)

            if filtro_equipamento is not None:
                condicoes.append("e.id_equipamento = ?")
                parametros.append(filtro_equipamento)

        if tipo == "inventario_unidade":
            if filtro_unidade is not None:
                condicoes.append("e.id_unidade = ?")
                parametros.append(filtro_unidade)

        where = ""

        if condicoes:
            where = " WHERE " + " AND ".join(condicoes)

        if tipo == "unidades":
            sql = """
                SELECT
                    u.nome,
                    u.categoria,
                    u.cnes,
                    CASE WHEN u.ativo = 1
                         THEN 'Ativa' ELSE 'Inativa' END,
                    (
                        SELECT COUNT(*)
                        FROM equipamentos e
                        WHERE e.id_unidade = u.id_unidade
                    ),
                    (
                        SELECT COUNT(*)
                        FROM ordens_servico o
                        WHERE o.id_unidade = u.id_unidade
                    )
                FROM unidades u
            """
            colunas = (
                "Unidade", "Categoria", "CNES", "Situação",
                "Equipamentos", "OS",
            )
            ordem = " ORDER BY u.nome COLLATE NOCASE"

        elif tipo == "equipamentos":
            sql = """
                SELECT
                    e.descricao,
                    e.patrimonio,
                    e.marca,
                    e.modelo,
                    e.numero_serie,
                    u.nome,
                    e.situacao,
                    (
                        SELECT COUNT(*)
                        FROM ordens_servico o
                        WHERE o.id_equipamento = e.id_equipamento
                    )
                FROM equipamentos e
                JOIN unidades u
                    ON u.id_unidade = e.id_unidade
            """
            colunas = (
                "Equipamento", "Patrimônio", "Marca", "Modelo",
                "Série", "Unidade atual", "Situação", "OS",
            )
            ordem = (
                " ORDER BY u.nome COLLATE NOCASE, "
                "e.descricao COLLATE NOCASE"
            )

        elif tipo == "inventario_unidade":
            sql = """
                SELECT
                    e.descricao,
                    e.patrimonio,
                    e.marca,
                    e.modelo,
                    e.numero_serie,
                    e.setor,
                    e.situacao
                FROM equipamentos e
                JOIN unidades u
                    ON u.id_unidade = e.id_unidade
            """
            colunas = (
                "Equipamento", "Patrimônio", "Marca", "Modelo",
                "Série", "Setor", "Situação",
            )
            ordem = " ORDER BY e.descricao COLLATE NOCASE"

        elif tipo in (
            "ordens",
            "os_unidade",
            "os_sem_equipamento",
        ):
            sql = """
                SELECT
                    COALESCE(NULLIF(o.numero_os, ''),
                             'Sem número'),
                    u.nome,
                    COALESCE(e.descricao,
                             NULLIF(o.descricao_equipamento, ''),
                             'Vínculo pendente'),
                    o.data_abertura,
                    o.tipo_manutencao,
                    o.situacao,
                    (
                        SELECT COUNT(*)
                        FROM anexos_os a
                        WHERE a.id_os = o.id_os
                    )
                FROM ordens_servico o
                JOIN unidades u
                    ON u.id_unidade = o.id_unidade
                LEFT JOIN equipamentos e
                    ON e.id_equipamento = o.id_equipamento
            """
            colunas = (
                "OS", "Unidade do atendimento", "Equipamento",
                "Data do atendimento", "Tipo", "Situação", "PDFs",
            )
            ordem = (
                " ORDER BY o.data_abertura DESC, o.id_os DESC"
            )

        else:
            sql = """
                SELECT
                    COALESCE(NULLIF(o.numero_os, ''),
                             'Sem número'),
                    u.nome,
                    o.data_abertura,
                    o.tipo_manutencao,
                    o.situacao,
                    (
                        SELECT COUNT(*)
                        FROM anexos_os a
                        WHERE a.id_os = o.id_os
                    )
                FROM ordens_servico o
                JOIN unidades u
                    ON u.id_unidade = o.id_unidade
                JOIN equipamentos e
                    ON e.id_equipamento = o.id_equipamento
            """
            colunas = (
                "OS", "Unidade do atendimento",
                "Data do atendimento", "Tipo", "Situação", "PDFs",
            )
            ordem = (
                " ORDER BY o.data_abertura DESC, o.id_os DESC"
            )

        return sql + where + ordem, colunas, parametros

    def buscar_linhas(
        tipo,
        filtro_unidade,
        filtro_equipamento,
        data_inicio,
        data_fim,
    ):
        sql, colunas, parametros = montar_consulta(
            tipo,
            filtro_unidade,
            filtro_equipamento,
            data_inicio,
            data_fim,
        )

        linhas = get_db().execute(
            sql, parametros
        ).fetchall()

        return colunas, [tuple(linha) for linha in linhas]

    def montar_pdf(
        titulo,
        colunas,
        linhas,
        filtros_texto,
    ):
        buffer = BytesIO()

        paisagem = tipo_usa_paisagem(titulo)

        documento = SimpleDocTemplate(
            buffer,
            pagesize=(
                landscape(A4) if paisagem else A4
            ),
            title=titulo,
            author="Gestão de Equipamentos Clínicos",
        )

        estilos = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            "TituloRelatorio",
            parent=estilos["Heading1"],
            alignment=TA_CENTER,
            fontSize=14,
        )

        estilo_filtros = ParagraphStyle(
            "FiltrosRelatorio",
            parent=estilos["Normal"],
            fontSize=9,
        )

        elementos = [
            Paragraph(
                "Secretaria Municipal de Saúde",
                estilos["Normal"],
            ),
            Paragraph(titulo, estilo_titulo),
            Spacer(1, 0.4 * cm),
            Paragraph(filtros_texto, estilo_filtros),
            Paragraph(
                "Emitido em: "
                + date.today().strftime("%d/%m/%Y"),
                estilos["Normal"],
            ),
            Spacer(1, 0.6 * cm),
        ]

        dados = [colunas]

        for linha in linhas:
            dados.append(
                [
                    formatar_data(valor)
                    if isinstance(valor, str)
                    and valor
                    and len(valor) == 10
                    and valor[4] == "-"
                    else (
                        "Não informado"
                        if valor in (None, "")
                        else str(valor)
                    )
                    for valor in linha
                ]
            )

        if len(linhas) == 0:
            dados.append(
                ["Nenhum registro encontrado"] * len(colunas)
            )

        tabela = Table(
            dados,
            repeatRows=1,
            colWidths=None,
        )

        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f4565")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS",
             (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f1f5f9")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))

        elementos.append(tabela)

        documento.build(elementos)
        buffer.seek(0)

        return buffer

    def tipo_usa_paisagem(titulo):
        return any(
            palavra in titulo
            for palavra in (
                "Equipamentos",
                "Histórico",
                "Inventário",
                "Ordens de serviço",
            )
        )

    @app.get("/relatorios")
    @login_obrigatorio
    def relatorios():
        (
            tipo,
            filtro_unidade,
            filtro_equipamento,
            data_inicio,
            data_fim,
        ) = ler_filtros()

        colunas, linhas = buscar_linhas(
            tipo,
            filtro_unidade,
            filtro_equipamento,
            data_inicio,
            data_fim,
        )

        db = get_db()

        return render_template_string(
            PAGINA_HTML,
            tipos=tipos,
            tipo=tipo,
            titulo=rotulos[tipo],
            colunas=colunas,
            linhas=linhas,
            unidades=db.execute(
                "SELECT id_unidade, nome FROM unidades "
                "ORDER BY nome COLLATE NOCASE"
            ).fetchall(),
            equipamentos=db.execute(
                """
                SELECT id_equipamento, descricao, patrimonio
                FROM equipamentos
                ORDER BY descricao COLLATE NOCASE
                """
            ).fetchall(),
            filtro_unidade=filtro_unidade,
            filtro_equipamento=filtro_equipamento,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    @app.get("/relatorios/pdf")
    @login_obrigatorio
    def relatorios_pdf():
        (
            tipo,
            filtro_unidade,
            filtro_equipamento,
            data_inicio,
            data_fim,
        ) = ler_filtros()

        colunas, linhas = buscar_linhas(
            tipo,
            filtro_unidade,
            filtro_equipamento,
            data_inicio,
            data_fim,
        )

        partes = []

        if filtro_unidade is not None:
            unidade = get_db().execute(
                "SELECT nome FROM unidades WHERE id_unidade = ?",
                (filtro_unidade,),
            ).fetchone()

            if unidade is not None:
                partes.append(
                    "Unidade: " + unidade["nome"]
                )

        if filtro_equipamento is not None:
            equipamento = get_db().execute(
                """
                SELECT descricao FROM equipamentos
                WHERE id_equipamento = ?
                """,
                (filtro_equipamento,),
            ).fetchone()

            if equipamento is not None:
                partes.append(
                    "Equipamento: "
                    + equipamento["descricao"]
                )

        if data_inicio:
            partes.append(
                "De: " + formatar_data(data_inicio)
            )

        if data_fim:
            partes.append(
                "Até: " + formatar_data(data_fim)
            )

        filtros_texto = (
            "Filtros: " + "; ".join(partes)
            if partes
            else "Filtros: todos os registros"
        )

        titulo = rotulos[tipo]
        buffer = montar_pdf(
            titulo, colunas, linhas, filtros_texto
        )

        nome = (
            "relatorio-"
            + tipo.replace("_", "-")
            + "-"
            + date.today().isoformat()
            + ".pdf"
        )

        resposta = send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nome,
        )

        resposta.headers["Cache-Control"] = "no-store"

        return resposta