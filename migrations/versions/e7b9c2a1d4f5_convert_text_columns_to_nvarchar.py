"""convert text columns to nvarchar for full unicode support

Revision ID: e7b9c2a1d4f5
Revises: 041f1abf6aef
Create Date: 2026-11-06 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7b9c2a1d4f5'
down_revision = '041f1abf6aef'
branch_labels = None
depends_on = None


def upgrade():
    # Convert tasks columns
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.alter_column('title',
               existing_type=sa.String(length=200),
               type_=sa.Unicode(length=200),
               existing_nullable=False)
        batch_op.alter_column('description',
               existing_type=sa.Text(),
               type_=sa.UnicodeText(),
               existing_nullable=True)

    # Convert boards columns
    with op.batch_alter_table('boards', schema=None) as batch_op:
        batch_op.alter_column('name',
               existing_type=sa.String(length=100),
               type_=sa.Unicode(length=100),
               existing_nullable=False)
        batch_op.alter_column('description',
               existing_type=sa.Text(),
               type_=sa.UnicodeText(),
               existing_nullable=True)

    # Convert comments column
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.alter_column('content',
               existing_type=sa.Text(),
               type_=sa.UnicodeText(),
               existing_nullable=False)


def downgrade():
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.alter_column('content',
               existing_type=sa.UnicodeText(),
               type_=sa.Text(),
               existing_nullable=False)

    with op.batch_alter_table('boards', schema=None) as batch_op:
        batch_op.alter_column('description',
               existing_type=sa.UnicodeText(),
               type_=sa.Text(),
               existing_nullable=True)
        batch_op.alter_column('name',
               existing_type=sa.Unicode(length=100),
               type_=sa.String(length=100),
               existing_nullable=False)

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.alter_column('description',
               existing_type=sa.UnicodeText(),
               type_=sa.Text(),
               existing_nullable=True)
        batch_op.alter_column('title',
               existing_type=sa.Unicode(length=200),
               type_=sa.String(length=200),
               existing_nullable=False)

