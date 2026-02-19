"""create_terraform_plans_table

Revision ID: 583158d738de
Revises: 5bc9853382fd
Create Date: 2026-02-18 02:08:44.065068

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '583158d738de'
down_revision = '5bc9853382fd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create terraform_plans table
    op.create_table(
        'terraform_plans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('original_requirements', sa.Text(), nullable=False),
        sa.Column('structured_requirements', JSONB, nullable=False),
        sa.Column('s3_prefix', sa.String(length=500), nullable=False),
        sa.Column('validation_passed', sa.Boolean(), nullable=True, default=False),
        sa.Column('validation_output', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='generating'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_terraform_plans_user_id'), 'terraform_plans', ['user_id'], unique=False)
    op.create_index(op.f('ix_terraform_plans_status'), 'terraform_plans', ['status'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_terraform_plans_status'), table_name='terraform_plans')
    op.drop_index(op.f('ix_terraform_plans_user_id'), table_name='terraform_plans')
    
    # Drop table
    op.drop_table('terraform_plans')
