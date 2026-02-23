"""create_deployments_table

Revision ID: 5245a315e841
Revises: 583158d738de
Create Date: 2026-02-19 01:16:13.537877

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '5245a315e841'
down_revision = '583158d738de'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create DeploymentStatus enum type (skip if already exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE deploymentstatus AS ENUM ('STARTED', 'RUNNING', 'SUCCESS', 'FAILED', 'DESTROYED', 'DESTROY_FAILED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create deployments table using raw SQL to avoid enum creation issues
    op.execute("""
        CREATE TABLE deployments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            terraform_plan_id UUID NOT NULL REFERENCES terraform_plans(id) ON DELETE CASCADE,
            aws_connection_id UUID REFERENCES aws_integrations(id) ON DELETE SET NULL,
            status deploymentstatus NOT NULL DEFAULT 'STARTED',
            output TEXT,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        );
    """)
    
    # Create individual indexes (Requirements 1.2, 1.3, 1.4)
    op.create_index(op.f('ix_deployments_user_id'), 'deployments', ['user_id'], unique=False)
    op.create_index(op.f('ix_deployments_terraform_plan_id'), 'deployments', ['terraform_plan_id'], unique=False)
    op.create_index(op.f('ix_deployments_status'), 'deployments', ['status'], unique=False)
    op.create_index(op.f('ix_deployments_aws_connection_id'), 'deployments', ['aws_connection_id'], unique=False)
    op.create_index(op.f('ix_deployments_created_at'), 'deployments', ['created_at'], unique=False)
    
    # Create composite index on (user_id, created_at) for efficient user history queries (Requirement 1.5)
    op.create_index('ix_deployments_user_created', 'deployments', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_deployments_user_created', table_name='deployments')
    op.drop_index(op.f('ix_deployments_created_at'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_aws_connection_id'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_status'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_terraform_plan_id'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_user_id'), table_name='deployments')
    
    # Drop table
    op.drop_table('deployments')
    
    # Drop enum type
    sa.Enum(name='deploymentstatus').drop(op.get_bind(), checkfirst=True)
