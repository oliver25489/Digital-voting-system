"""Add school_id to EndUser

Revision ID: 4ce6d4d5c896
Revises: 30b178bbdb54
Create Date: 2025-07-21 15:16:32.550994

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ce6d4d5c896'
down_revision = '30b178bbdb54'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('end_users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('school_id', sa.String(length=50), nullable=False))
        batch_op.create_unique_constraint(None, ['school_id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('end_users', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('school_id')

    # ### end Alembic commands ###
