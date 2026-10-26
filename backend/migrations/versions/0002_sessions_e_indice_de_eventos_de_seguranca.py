"""sessoes e indice de eventos de seguranca

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22 21:50:44.957793
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('sessoes',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('criada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ultimo_acesso_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revogada_em', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('expira_em > criada_em', name=op.f('ck_sessoes_expiracao_apos_criacao')),
    sa.CheckConstraint('length(token_hash) = 64', name=op.f('ck_sessoes_token_hash_sha256')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_sessoes_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sessoes')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_sessoes_token_hash'))
    )
    op.create_index(op.f('ix_sessoes_usuario_id'), 'sessoes', ['usuario_id'], unique=False)
    op.create_index('ix_auditoria_tipo_evento_ocorrido_em', 'auditoria', ['tipo_evento', 'ocorrido_em'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_auditoria_tipo_evento_ocorrido_em', table_name='auditoria')
    op.drop_index(op.f('ix_sessoes_usuario_id'), table_name='sessoes')
    op.drop_table('sessoes')