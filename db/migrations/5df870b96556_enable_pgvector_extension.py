"""enable pgvector extension

Revision ID: 5df870b96556
Revises: 7e3470070211
Create Date: 2026-07-01 01:41:36.049138

"""
from alembic import op
import sqlalchemy as sa


revision = '5df870b96556'
down_revision = '7e3470070211'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade():
    op.execute("DROP EXTENSION IF EXISTS vector")
