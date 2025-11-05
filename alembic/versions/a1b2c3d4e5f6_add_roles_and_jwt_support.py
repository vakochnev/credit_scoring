"""add roles and jwt support

Revision ID: a1b2c3d4e5f6
Revises: 249d77c3f559
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '249d77c3f559'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add roles and JWT support."""
    # Добавляем поля в таблицу users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(), nullable=False, server_default='user'))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_login', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - remove roles and JWT support."""
    # Удаляем добавленные поля
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_login')
        batch_op.drop_column('created_at')
        batch_op.drop_column('is_active')
        batch_op.drop_column('role')

