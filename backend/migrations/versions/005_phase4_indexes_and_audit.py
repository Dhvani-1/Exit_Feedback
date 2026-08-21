"""phase4 indexes and audit columns

Revision ID: 005_phase4_indexes_and_audit
Revises: 004_simplify_employee_schema
Create Date: 2026-08-21 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '005_phase4_indexes_and_audit'
down_revision = '004_simplify_employee_schema'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    # 1. Add actor_type and actor_id to audit_logs if missing
    audit_columns = [col['name'] for col in inspector.get_columns('audit_logs')]
    if 'actor_type' not in audit_columns:
        op.add_column('audit_logs', sa.Column('actor_type', sa.String(length=50), nullable=True))
    if 'actor_id' not in audit_columns:
        op.add_column('audit_logs', sa.Column('actor_id', sa.String(length=100), nullable=True))

    # 2. Add composite indexes for Phase 4 queries safely
    emp_indexes = [idx['name'] for idx in inspector.get_indexes('employees')]
    if 'ix_employees_status_due' not in emp_indexes:
        op.create_index('ix_employees_status_due', 'employees', ['status', 'feedback_due_date'])

    fb_indexes = [idx['name'] for idx in inspector.get_indexes('feedback_records')]
    if 'ix_feedback_status_expiry' not in fb_indexes:
        op.create_index('ix_feedback_status_expiry', 'feedback_records', ['status', 'expires_at', 'submitted_at'])

    email_indexes = [idx['name'] for idx in inspector.get_indexes('email_jobs')]
    if 'ix_email_jobs_status_type_scheduled' not in email_indexes:
        op.create_index('ix_email_jobs_status_type_scheduled', 'email_jobs', ['status', 'email_type', 'scheduled_at'])

    audit_indexes = [idx['name'] for idx in inspector.get_indexes('audit_logs')]
    if 'ix_audit_logs_emp_created' not in audit_indexes:
        op.create_index('ix_audit_logs_emp_created', 'audit_logs', ['employee_id', 'created_at'])


def downgrade():
    op.drop_index('ix_audit_logs_emp_created', table_name='audit_logs', if_exists=True)
    op.drop_index('ix_email_jobs_status_type_scheduled', table_name='email_jobs', if_exists=True)
    op.drop_index('ix_feedback_status_expiry', table_name='feedback_records', if_exists=True)
    op.drop_index('ix_employees_status_due', table_name='employees', if_exists=True)

    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    audit_columns = [col['name'] for col in inspector.get_columns('audit_logs')]
    if 'actor_id' in audit_columns:
        op.drop_column('audit_logs', 'actor_id')
    if 'actor_type' in audit_columns:
        op.drop_column('audit_logs', 'actor_type')
