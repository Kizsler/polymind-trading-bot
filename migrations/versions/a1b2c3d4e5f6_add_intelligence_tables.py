"""add intelligence tables

Revision ID: a1b2c3d4e5f6
Revises: db85214b9e26
Create Date: 2026-01-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'db85214b9e26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add wallet control columns
    op.add_column('wallets', sa.Column('scale_factor', sa.Float(), nullable=False, server_default='1.0'))
    op.add_column('wallets', sa.Column('max_trade_size', sa.Float(), nullable=True))
    op.add_column('wallets', sa.Column('min_confidence', sa.Float(), nullable=False, server_default='0.0'))

    # Create market_filters table
    op.create_table('market_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filter_type', sa.String(length=20), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create market_mappings table
    op.create_table('market_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('polymarket_id', sa.String(length=255), nullable=True),
        sa.Column('kalshi_id', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_mappings_polymarket_id'), 'market_mappings', ['polymarket_id'], unique=False)
    op.create_index(op.f('ix_market_mappings_kalshi_id'), 'market_mappings', ['kalshi_id'], unique=False)

    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('signal_id', sa.String(length=255), nullable=True),
        sa.Column('market_id', sa.String(length=200), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('requested_size', sa.Float(), nullable=False),
        sa.Column('filled_size', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('requested_price', sa.Float(), nullable=False),
        sa.Column('filled_price', sa.Float(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_external_id'), 'orders', ['external_id'], unique=False)
    op.create_index(op.f('ix_orders_signal_id'), 'orders', ['signal_id'], unique=False)
    op.create_index(op.f('ix_orders_market_id'), 'orders', ['market_id'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop orders table
    op.drop_index(op.f('ix_orders_status'), table_name='orders')
    op.drop_index(op.f('ix_orders_market_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_signal_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_external_id'), table_name='orders')
    op.drop_table('orders')

    # Drop market_mappings table
    op.drop_index(op.f('ix_market_mappings_kalshi_id'), table_name='market_mappings')
    op.drop_index(op.f('ix_market_mappings_polymarket_id'), table_name='market_mappings')
    op.drop_table('market_mappings')

    # Drop market_filters table
    op.drop_table('market_filters')

    # Remove wallet control columns
    op.drop_column('wallets', 'min_confidence')
    op.drop_column('wallets', 'max_trade_size')
    op.drop_column('wallets', 'scale_factor')
