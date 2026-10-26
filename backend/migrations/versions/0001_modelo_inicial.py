"""modelo inicial: cadastros, liberacoes, historico e auditoria

Revision ID: 0001
Revises: 
Create Date: 2026-10-22 02:53:50.509618
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('alunos',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('nome_completo', sa.String(length=200), nullable=False),
    sa.Column('matricula_institucional', sa.String(length=50), nullable=True),
    sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_alunos')),
    sa.UniqueConstraint('matricula_institucional', name=op.f('uq_alunos_matricula_institucional'))
    )
    op.create_table('anos_letivos',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('ano', sa.Integer(), nullable=False),
    sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_anos_letivos')),
    sa.UniqueConstraint('ano', name=op.f('uq_anos_letivos_ano'))
    )
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('senha_hash', sa.String(length=255), nullable=False),
    sa.Column('perfil', sa.String(length=20), nullable=False),
    sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("perfil IN ('RESPONSAVEL', 'ADMIN')", name=op.f('ck_usuarios_perfil')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usuarios')),
    sa.UniqueConstraint('email', name=op.f('uq_usuarios_email'))
    )
    op.create_table('auditoria',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('ocorrido_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('perfil', sa.String(length=20), nullable=True),
    sa.Column('tipo_evento', sa.String(length=60), nullable=False),
    sa.Column('entidade', sa.String(length=60), nullable=False),
    sa.Column('entidade_id', sa.BigInteger(), nullable=True),
    sa.Column('detalhes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("perfil IN ('RESPONSAVEL', 'ADMIN')", name=op.f('ck_auditoria_perfil')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_auditoria_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auditoria'))
    )
    op.create_table('liberacoes',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.Date(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('atualizado_por_usuario_id', sa.Integer(), nullable=True),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("estado IN ('LIBERADO', 'CANCELADO')", name=op.f('ck_liberacoes_estado')),
    sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_liberacoes_aluno_id_alunos')),
    sa.ForeignKeyConstraint(['atualizado_por_usuario_id'], ['usuarios.id'], name=op.f('fk_liberacoes_atualizado_por_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_liberacoes')),
    sa.UniqueConstraint('aluno_id', 'data', name=op.f('uq_liberacoes_aluno_id'))
    )
    op.create_table('responsaveis',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('nome_completo', sa.String(length=200), nullable=False),
    sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_responsaveis_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_responsaveis')),
    sa.UniqueConstraint('usuario_id', name=op.f('uq_responsaveis_usuario_id'))
    )
    op.create_table('turmas',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('identificacao', sa.String(length=50), nullable=False),
    sa.Column('ano_escolar', sa.Integer(), nullable=False),
    sa.Column('ano_letivo_id', sa.Integer(), nullable=False),
    sa.Column('turno', sa.String(length=20), nullable=False),
    sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("turno IN ('MANHA', 'NOITE')", name=op.f('ck_turmas_turno')),
    sa.CheckConstraint('ano_escolar > 0', name=op.f('ck_turmas_ano_escolar_positivo')),
    sa.ForeignKeyConstraint(['ano_letivo_id'], ['anos_letivos.id'], name=op.f('fk_turmas_ano_letivo_id_anos_letivos')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_turmas')),
    sa.UniqueConstraint('ano_letivo_id', 'identificacao', name=op.f('uq_turmas_ano_letivo_id')),
    sa.UniqueConstraint('id', 'ano_letivo_id', name=op.f('uq_turmas_id'))
    )
    op.create_table('eventos_agenda',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('turma_id', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('data_fim', sa.Date(), nullable=False),
    sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('data_fim >= data_inicio', name=op.f('ck_eventos_agenda_periodo_valido')),
    sa.ForeignKeyConstraint(['turma_id'], ['turmas.id'], name=op.f('fk_eventos_agenda_turma_id_turmas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_eventos_agenda'))
    )
    op.create_index('ix_eventos_agenda_turma_periodo', 'eventos_agenda', ['turma_id', 'data_inicio', 'data_fim'], unique=False)
    op.create_table('historico_liberacoes',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('liberacao_id', sa.Integer(), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('perfil', sa.String(length=20), nullable=False),
    sa.Column('ocorrido_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('estado_anterior', sa.String(length=20), nullable=True),
    sa.Column('novo_estado', sa.String(length=20), nullable=False),
    sa.Column('tipo_acao', sa.String(length=20), nullable=False),
    sa.Column('motivo', sa.Text(), nullable=True),
    sa.CheckConstraint("estado_anterior IN ('LIBERADO', 'CANCELADO')", name=op.f('ck_historico_liberacoes_estado_anterior')),
    sa.CheckConstraint("novo_estado IN ('LIBERADO', 'CANCELADO')", name=op.f('ck_historico_liberacoes_novo_estado')),
    sa.CheckConstraint("perfil IN ('RESPONSAVEL', 'ADMIN')", name=op.f('ck_historico_liberacoes_perfil')),
    sa.CheckConstraint("tipo_acao <> 'CORRECAO_ADMIN' OR (motivo IS NOT NULL AND btrim(motivo) <> '')", name=op.f('ck_historico_liberacoes_motivo_da_correcao')),
    sa.CheckConstraint("tipo_acao IN ('LIBERACAO', 'CANCELAMENTO', 'CORRECAO_ADMIN')", name=op.f('ck_historico_liberacoes_tipo_acao')),
    sa.CheckConstraint('estado_anterior IS NULL OR estado_anterior <> novo_estado', name=op.f('ck_historico_liberacoes_mudanca_real')),
    sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_historico_liberacoes_aluno_id_alunos')),
    sa.ForeignKeyConstraint(['liberacao_id'], ['liberacoes.id'], name=op.f('fk_historico_liberacoes_liberacao_id_liberacoes')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_historico_liberacoes_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_historico_liberacoes'))
    )
    op.create_index(op.f('ix_historico_liberacoes_aluno_id'), 'historico_liberacoes', ['aluno_id'], unique=False)
    op.create_index(op.f('ix_historico_liberacoes_liberacao_id'), 'historico_liberacoes', ['liberacao_id'], unique=False)
    op.create_table('matriculas',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('turma_id', sa.Integer(), nullable=False),
    sa.Column('ano_letivo_id', sa.Integer(), nullable=False),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('data_fim', sa.Date(), nullable=True),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('data_fim IS NULL OR data_fim >= data_inicio', name=op.f('ck_matriculas_periodo_valido')),
    sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_matriculas_aluno_id_alunos')),
    sa.ForeignKeyConstraint(['turma_id', 'ano_letivo_id'], ['turmas.id', 'turmas.ano_letivo_id'], name=op.f('fk_matriculas_turma_id_turmas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_matriculas'))
    )
    op.create_index(op.f('ix_matriculas_turma_id'), 'matriculas', ['turma_id'], unique=False)
    op.create_index('uq_matriculas_aberta_por_aluno_e_ano', 'matriculas', ['aluno_id', 'ano_letivo_id'], unique=True, postgresql_where=sa.text('data_fim IS NULL'))
    op.create_table('responsaveis_alunos',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('responsavel_id', sa.Integer(), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('vigente_desde', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revogado_em', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('revogado_em IS NULL OR revogado_em > vigente_desde', name=op.f('ck_responsaveis_alunos_revogacao_apos_inicio')),
    sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_responsaveis_alunos_aluno_id_alunos')),
    sa.ForeignKeyConstraint(['responsavel_id'], ['responsaveis.id'], name=op.f('fk_responsaveis_alunos_responsavel_id_responsaveis')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_responsaveis_alunos'))
    )
    op.create_index(op.f('ix_responsaveis_alunos_aluno_id'), 'responsaveis_alunos', ['aluno_id'], unique=False)
    op.create_index('uq_responsaveis_alunos_vinculo_ativo', 'responsaveis_alunos', ['responsavel_id', 'aluno_id'], unique=True, postgresql_where=sa.text('revogado_em IS NULL'))
    # Historico e auditoria sao append-only: UPDATE, DELETE e TRUNCATE sao bloqueados
    # pelo proprio banco, valendo ate para acessos diretos fora da aplicacao.
    op.execute(
        """
        CREATE FUNCTION bloquear_alteracao_historico() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'A tabela % e append-only: % nao e permitido', TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    for tabela in ("historico_liberacoes", "auditoria"):
        op.execute(
            f"CREATE TRIGGER trg_{tabela}_append_only BEFORE UPDATE OR DELETE ON {tabela} "
            "FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao_historico()"
        )
        op.execute(
            f"CREATE TRIGGER trg_{tabela}_sem_truncate BEFORE TRUNCATE ON {tabela} "
            "FOR EACH STATEMENT EXECUTE FUNCTION bloquear_alteracao_historico()"
        )


def downgrade() -> None:
    op.drop_index('uq_responsaveis_alunos_vinculo_ativo', table_name='responsaveis_alunos', postgresql_where=sa.text('revogado_em IS NULL'))
    op.drop_index(op.f('ix_responsaveis_alunos_aluno_id'), table_name='responsaveis_alunos')
    op.drop_table('responsaveis_alunos')
    op.drop_index('uq_matriculas_aberta_por_aluno_e_ano', table_name='matriculas', postgresql_where=sa.text('data_fim IS NULL'))
    op.drop_index(op.f('ix_matriculas_turma_id'), table_name='matriculas')
    op.drop_table('matriculas')
    op.drop_index(op.f('ix_historico_liberacoes_liberacao_id'), table_name='historico_liberacoes')
    op.drop_index(op.f('ix_historico_liberacoes_aluno_id'), table_name='historico_liberacoes')
    op.drop_table('historico_liberacoes')
    op.drop_index('ix_eventos_agenda_turma_periodo', table_name='eventos_agenda')
    op.drop_table('eventos_agenda')
    op.drop_table('turmas')
    op.drop_table('responsaveis')
    op.drop_table('liberacoes')
    op.drop_table('auditoria')
    op.drop_table('usuarios')
    op.drop_table('anos_letivos')
    op.drop_table('alunos')
    # Os triggers saem junto com as tabelas; resta remover a funcao.
    op.execute("DROP FUNCTION bloquear_alteracao_historico()")