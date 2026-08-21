"""Email system schema creation for email_jobs, email_templates, and system_settings

Revision ID: 002_email_system_schema
Revises: 001_initial_schema
Create Date: 2026-08-20 14:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime
from alembic import op
import sqlalchemy as sa

revision: str = '002_email_system_schema'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create email_templates table
    op.create_table(
        'email_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('template_key', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False, server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_templates_id'), 'email_templates', ['id'], unique=False)
    op.create_index(op.f('ix_email_templates_template_key'), 'email_templates', ['template_key'], unique=True)

    # 2. Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_id'), 'system_settings', ['id'], unique=False)
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # 3. Create email_jobs table
    op.create_table(
        'email_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('email_type', sa.String(length=50), nullable=False, server_default='EXIT_FEEDBACK_INITIAL'),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('recipient_email', sa.String(length=100), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='SCHEDULED'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('worker_id', sa.String(length=100), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('template_version', sa.String(length=20), nullable=True, server_default='1.0'),
        sa.Column('message_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'email_type', name='uq_employee_email_type')
    )
    op.create_index(op.f('ix_email_jobs_id'), 'email_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_email_jobs_employee_id'), 'email_jobs', ['employee_id'], unique=False)
    op.create_index(op.f('ix_email_jobs_idempotency_key'), 'email_jobs', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_email_jobs_recipient_email'), 'email_jobs', ['recipient_email'], unique=False)
    op.create_index(op.f('ix_email_jobs_scheduled_at'), 'email_jobs', ['scheduled_at'], unique=False)
    op.create_index(op.f('ix_email_jobs_status'), 'email_jobs', ['status'], unique=False)

    # Seed initial template
    email_templates_table = sa.table(
        'email_templates',
        sa.column('template_key', sa.String),
        sa.column('subject', sa.String),
        sa.column('body', sa.Text),
        sa.column('version', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )
    op.bulk_insert(
        email_templates_table,
        [{
            'template_key': 'EXIT_FEEDBACK_INITIAL',
            'subject': 'Confidential Employee Exit Feedback Request - {{company_name}}',
            'body': '''<p>Dear {{employee_name}},</p>
<p>Thank you for your valuable service with <strong>{{company_name}}</strong> (Employee ID: {{employee_id}}).</p>
<p>As part of our exit process following your last working date on <strong>{{last_working_date}}</strong>, we invite you to share your feedback to help us improve our workplace culture.</p>
<p><a href="{{feedback_form_url}}?emp={{employee_id}}" style="background-color:#0284c7; color:#ffffff; padding:10px 20px; text-decoration:none; border-radius:5px; display:inline-block; font-weight:bold;">Complete Exit Feedback Form</a></p>
<p>If the button above does not work, please copy and paste the following URL into your browser:<br>{{feedback_form_url}}?emp={{employee_id}}</p>
<p>Best regards,<br>Human Resources Team<br>{{company_name}}</p>''',
            'version': '1.0',
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }]
    )

    # Seed default system settings
    system_settings_table = sa.table(
        'system_settings',
        sa.column('key', sa.String),
        sa.column('value', sa.Text),
        sa.column('description', sa.String),
        sa.column('updated_at', sa.DateTime)
    )
    op.bulk_insert(
        system_settings_table,
        [
            {'key': 'company_name', 'value': 'Laxmi Organics Industries Ltd', 'description': 'Company Name', 'updated_at': datetime.utcnow()},
            {'key': 'feedback_form_url', 'value': 'https://feedback.company.com/exit-form', 'description': 'Feedback Form Base URL', 'updated_at': datetime.utcnow()},
            {'key': 'sender_email', 'value': 'hr@company.com', 'description': 'Sender Email Address', 'updated_at': datetime.utcnow()},
            {'key': 'sender_name', 'value': 'HR Department', 'description': 'Sender Name', 'updated_at': datetime.utcnow()},
            {'key': 'email_send_hour', 'value': '9', 'description': 'Daily send hour (0-23)', 'updated_at': datetime.utcnow()},
            {'key': 'timezone', 'value': 'Asia/Kolkata', 'description': 'Application Timezone (IANA format)', 'updated_at': datetime.utcnow()},
            {'key': 'weekend_behavior', 'value': 'SEND_ON_DUE_DATE', 'description': 'Weekend behavior option', 'updated_at': datetime.utcnow()},
        ]
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_email_jobs_status'), table_name='email_jobs')
    op.drop_index(op.f('ix_email_jobs_scheduled_at'), table_name='email_jobs')
    op.drop_index(op.f('ix_email_jobs_recipient_email'), table_name='email_jobs')
    op.drop_index(op.f('ix_email_jobs_idempotency_key'), table_name='email_jobs')
    op.drop_index(op.f('ix_email_jobs_employee_id'), table_name='email_jobs')
    op.drop_index(op.f('ix_email_jobs_id'), table_name='email_jobs')
    op.drop_table('email_jobs')

    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_index(op.f('ix_system_settings_id'), table_name='system_settings')
    op.drop_table('system_settings')

    op.drop_index(op.f('ix_email_templates_template_key'), table_name='email_templates')
    op.drop_index(op.f('ix_email_templates_id'), table_name='email_templates')
    op.drop_table('email_templates')
