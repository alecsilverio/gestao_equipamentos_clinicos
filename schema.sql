-- =========================================================
-- USUÁRIOS DO SISTEMA
-- =========================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,

    email TEXT NOT NULL COLLATE NOCASE UNIQUE,

    senha_hash TEXT NOT NULL,

    papel TEXT NOT NULL
        CHECK (
            papel IN (
                'administrador_principal',
                'consulta'
            )
        ),

    ativo INTEGER NOT NULL DEFAULT 1
        CHECK (ativo IN (0, 1)),

    primeiro_acesso INTEGER NOT NULL DEFAULT 1
        CHECK (primeiro_acesso IN (0, 1)),

    versao_sessao INTEGER NOT NULL DEFAULT 1,

    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    ultimo_acesso TEXT
);