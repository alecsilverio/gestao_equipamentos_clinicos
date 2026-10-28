import sqlite3

import click


SITUACOES_OS = (
    "Aberta",
    "Em andamento",
    "Concluída",
    "Cancelada",
)

TIPOS_MANUTENCAO = (
    "Não informado",
    "Preventiva",
    "Corretiva",
)

MODALIDADES_OS = (
    "Não informada",
    "Interna",
    "Externa",
)


SQL_ORDENS_SERVICO = """
CREATE TABLE IF NOT EXISTS ordens_servico (
    id_os INTEGER PRIMARY KEY AUTOINCREMENT,

    numero_os TEXT NOT NULL
        CHECK (LENGTH(TRIM(numero_os)) > 0),

    id_unidade INTEGER NOT NULL,

    id_equipamento INTEGER,

    descricao_equipamento TEXT NOT NULL DEFAULT '',

    patrimonio_informado TEXT NOT NULL DEFAULT '',

    tipo_manutencao TEXT NOT NULL DEFAULT 'Não informado'
        CHECK (
            tipo_manutencao IN (
                'Não informado',
                'Preventiva',
                'Corretiva'
            )
        ),

    modalidade TEXT NOT NULL DEFAULT 'Não informada'
        CHECK (
            modalidade IN (
                'Não informada',
                'Interna',
                'Externa'
            )
        ),

    empresa_responsavel TEXT NOT NULL DEFAULT '',

    tecnico_responsavel TEXT NOT NULL DEFAULT '',

    data_abertura TEXT NOT NULL
        CHECK (LENGTH(TRIM(data_abertura)) > 0),

    data_conclusao TEXT,

    situacao TEXT NOT NULL DEFAULT 'Aberta'
        CHECK (
            situacao IN (
                'Aberta',
                'Em andamento',
                'Concluída',
                'Cancelada'
            )
        ),

    problema_relatado TEXT NOT NULL DEFAULT '',

    servico_realizado TEXT NOT NULL DEFAULT '',

    observacoes TEXT NOT NULL DEFAULT '',

    criado_por INTEGER NOT NULL,

    atualizado_por INTEGER NOT NULL,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        situacao <> 'Concluída'
        OR (
            data_conclusao IS NOT NULL
            AND LENGTH(TRIM(data_conclusao)) > 0
        )
    ),

    FOREIGN KEY (id_unidade)
        REFERENCES unidades(id_unidade)
        ON DELETE RESTRICT,

    FOREIGN KEY (id_equipamento)
        REFERENCES equipamentos(id_equipamento)
        ON DELETE RESTRICT,

    FOREIGN KEY (criado_por)
        REFERENCES usuarios(id_usuario)
        ON DELETE RESTRICT,

    FOREIGN KEY (atualizado_por)
        REFERENCES usuarios(id_usuario)
        ON DELETE RESTRICT
)
"""


SQL_ANEXOS_OS = """
CREATE TABLE IF NOT EXISTS anexos_os (
    id_anexo INTEGER PRIMARY KEY AUTOINCREMENT,

    id_os INTEGER NOT NULL,

    nome_original TEXT NOT NULL,

    nome_armazenado TEXT NOT NULL UNIQUE,

    tamanho_bytes INTEGER NOT NULL
        CHECK (tamanho_bytes > 0),

    enviado_por INTEGER NOT NULL,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_os)
        REFERENCES ordens_servico(id_os)
        ON DELETE RESTRICT,

    FOREIGN KEY (enviado_por)
        REFERENCES usuarios(id_usuario)
        ON DELETE RESTRICT
)
"""


INDICES_OS = (
    """
    CREATE INDEX IF NOT EXISTS idx_os_unidade
    ON ordens_servico(id_unidade)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_os_equipamento
    ON ordens_servico(id_equipamento)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_os_numero
    ON ordens_servico(numero_os)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_os_situacao
    ON ordens_servico(situacao)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_os_data_abertura
    ON ordens_servico(data_abertura)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_anexos_os_ordem
    ON anexos_os(id_os)
    """,
)


def registrar_ordens_servico(
    app,
    get_db,
    login_obrigatorio,
):
    """Registra o módulo de ordens de serviço."""

    @app.cli.command("inicializar-os")
    def inicializar_os():
        """Cria as tabelas de OS e anexos sem apagar dados."""

        db = get_db()

        tabelas_obrigatorias = (
            "usuarios",
            "unidades",
            "equipamentos",
        )

        for nome in tabelas_obrigatorias:
            existe = db.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                (nome,),
            ).fetchone()

            if existe is None:
                raise click.ClickException(
                    f"A tabela {nome} não existe. "
                    "Inicialize o módulo correspondente primeiro."
                )

        foreign_keys = db.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

        if foreign_keys != 1:
            raise click.ClickException(
                "A proteção de chaves estrangeiras está desativada. "
                "Confira PRAGMA foreign_keys = ON na função get_db()."
            )

        try:
            db.execute("BEGIN IMMEDIATE")

            db.execute(SQL_ORDENS_SERVICO)
            db.execute(SQL_ANEXOS_OS)

            for sql in INDICES_OS:
                db.execute(sql)

            db.commit()

        except sqlite3.Error as erro:
            db.rollback()

            raise click.ClickException(
                f"Não foi possível inicializar as OS: {erro}"
            ) from erro

        total_os = db.execute(
            "SELECT COUNT(*) FROM ordens_servico"
        ).fetchone()[0]

        total_anexos = db.execute(
            "SELECT COUNT(*) FROM anexos_os"
        ).fetchone()[0]

        click.echo("Estrutura de ordens de serviço pronta.")
        click.echo("Equipamento opcional; unidade obrigatória.")
        click.echo(f"OS existentes: {total_os}")
        click.echo(f"Anexos existentes: {total_anexos}")
        click.echo("Nenhum cadastro existente foi apagado.")

    @app.cli.command("verificar-os")
    def verificar_os():
        """Confere as tabelas e seus vínculos."""

        db = get_db()

        try:
            total_os = db.execute(
                "SELECT COUNT(*) FROM ordens_servico"
            ).fetchone()[0]

            sem_equipamento = db.execute(
                """
                SELECT COUNT(*)
                FROM ordens_servico
                WHERE id_equipamento IS NULL
                """
            ).fetchone()[0]

            total_anexos = db.execute(
                "SELECT COUNT(*) FROM anexos_os"
            ).fetchone()[0]

            erros_os = db.execute(
                "PRAGMA foreign_key_check(ordens_servico)"
            ).fetchall()

            erros_anexos = db.execute(
                "PRAGMA foreign_key_check(anexos_os)"
            ).fetchall()

        except sqlite3.Error as erro:
            raise click.ClickException(
                f"Não foi possível verificar as OS: {erro}"
            ) from erro

        if erros_os or erros_anexos:
            raise click.ClickException(
                "Foram encontrados vínculos inválidos. "
                "Não altere nem exclua registros antes de verificar."
            )

        click.echo(f"Total de OS: {total_os}")
        click.echo(
            f"OS sem equipamento vinculado: {sem_equipamento}"
        )
        click.echo(f"Total de anexos: {total_anexos}")
        click.echo("Verificação concluída: vínculos válidos.")


    from os_telas import registrar_telas_os

    registrar_telas_os(
        app,
        get_db,
        login_obrigatorio,
        SITUACOES_OS,
        TIPOS_MANUTENCAO,
        MODALIDADES_OS,
    )