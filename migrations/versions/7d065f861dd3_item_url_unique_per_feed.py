"""Item URL unique per feed, not globally.

Revision ID: 7d065f861dd3
Revises: 01f04eb3cb6d
Create Date: 2022-03-17 23:53:50.263688

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d065f861dd3'
down_revision = '01f04eb3cb6d'
branch_labels = None
depends_on = None

naming_convention = {
    "uq":
    "uq_%(table_name)s_%(column_0_name)s",
}

def upgrade():
    with op.batch_alter_table("items", recreate='always', naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint('uq_items_url', type_='unique')
        batch_op.create_unique_constraint('uq_items_feed_id', ['feed_id', 'url'])

def downgrade():
    with op.batch_alter_table("items", recreate='always', naming_convention=naming_convention) as batch_op:
        batch_op.create_unique_constraint('uq_items_url', ['url'])
        batch_op.drop_constraint('uq_items_feed_id', type_='unique')
