"""simplify employee schema

Revision ID: 004_simplify_employee_schema
Revises: 003_feedback_system_schema
Create Date: 2026-08-20 17:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '004_simplify_employee_schema'
down_revision = '003_feedback_system_schema'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('employees')]

    op.drop_index('ix_employees_employee_id', table_name='employees', if_exists=True)
    op.drop_index('ix_employees_employee_name', table_name='employees', if_exists=True)
    op.drop_index('ix_employees_department', table_name='employees', if_exists=True)

    if 'full_name' not in existing_columns:
        with op.batch_alter_table('employees', schema=None) as batch_op:
            batch_op.add_column(sa.Column('full_name', sa.String(length=100), nullable=True))

    if 'employee_name' in existing_columns:
        op.execute("UPDATE employees SET full_name = employee_name WHERE full_name IS NULL")

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('full_name', nullable=False)
        batch_op.create_index(batch_op.f('ix_employees_full_name'), ['full_name'], unique=False)
        if 'employee_id' in existing_columns:
            batch_op.drop_column('employee_id')
        if 'employee_name' in existing_columns:
            batch_op.drop_column('employee_name')
        if 'department' in existing_columns:
            batch_op.drop_column('department')
        if 'designation' in existing_columns:
            batch_op.drop_column('designation')
        if 'manager' in existing_columns:
            batch_op.drop_column('manager')
        if 'location' in existing_columns:
            batch_op.drop_column('location')
        batch_op.create_unique_constraint('uq_personal_email_last_working_date', ['personal_email', 'last_working_date'])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('employees')]

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_constraint('uq_personal_email_last_working_date', type_='unique')
        batch_op.drop_index(batch_op.f('ix_employees_full_name'))
        batch_op.add_column(sa.Column('location', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('manager', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('designation', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('department', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('employee_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('employee_id', sa.String(length=50), nullable=True))

    op.execute("UPDATE employees SET employee_name = full_name WHERE employee_name IS NULL")
    op.execute("UPDATE employees SET employee_id = 'EMP-' || id WHERE employee_id IS NULL")

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.create_index('ix_employees_employee_id', ['employee_id'], unique=True)
        batch_op.create_index('ix_employees_employee_name', ['employee_name'], unique=False)
        batch_op.create_index('ix_employees_department', ['department'], unique=False)
        batch_op.drop_column('full_name')
