"""Initial schema creation for users and employees tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='HR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 2. Create employees table
    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.String(length=50), nullable=False),
        sa.Column('employee_name', sa.String(length=100), nullable=False),
        sa.Column('personal_email', sa.String(length=100), nullable=False),
        sa.Column('department', sa.String(length=50), nullable=False),
        sa.Column('designation', sa.String(length=50), nullable=False),
        sa.Column('manager', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('last_working_date', sa.Date(), nullable=False),
        sa.Column('feedback_due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='SCHEDULED'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)
    op.create_index(op.f('ix_employees_employee_id'), 'employees', ['employee_id'], unique=True)
    op.create_index(op.f('ix_employees_employee_name'), 'employees', ['employee_name'], unique=False)
    op.create_index(op.f('ix_employees_personal_email'), 'employees', ['personal_email'], unique=False)
    op.create_index(op.f('ix_employees_department'), 'employees', ['department'], unique=False)
    op.create_index(op.f('ix_employees_last_working_date'), 'employees', ['last_working_date'], unique=False)
    op.create_index(op.f('ix_employees_feedback_due_date'), 'employees', ['feedback_due_date'], unique=False)
    op.create_index(op.f('ix_employees_status'), 'employees', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_employees_status'), table_name='employees')
    op.drop_index(op.f('ix_employees_feedback_due_date'), table_name='employees')
    op.drop_index(op.f('ix_employees_last_working_date'), table_name='employees')
    op.drop_index(op.f('ix_employees_department'), table_name='employees')
    op.drop_index(op.f('ix_employees_personal_email'), table_name='employees')
    op.drop_index(op.f('ix_employees_employee_name'), table_name='employees')
    op.drop_index(op.f('ix_employees_employee_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_id'), table_name='employees')
    op.drop_table('employees')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
