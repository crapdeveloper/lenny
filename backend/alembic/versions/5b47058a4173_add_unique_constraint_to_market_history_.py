"""Add unique constraint to market_history table

Revision ID: 5b47058a4173
Revises: 6c65d5fb3c1b
Create Date: 2025-12-03 15:43:16.784847

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b47058a4173"
down_revision: Union[str, Sequence[str], None] = "6c65d5fb3c1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
