"""Feedback collection & reminder management schema

Revision ID: 003_feedback_system_schema
Revises: 002_email_system_schema
Create Date: 2026-08-20 17:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime
from alembic import op
import sqlalchemy as sa

revision: str = '003_feedback_system_schema'
down_revision: Union[str, None] = '002_email_system_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create feedback_records table
    op.create_table(
        'feedback_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('feedback_token', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('form_url', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('submission_source', sa.String(length=50), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', name='uq_feedback_employee_id'),
        sa.UniqueConstraint('feedback_token', name='uq_feedback_token')
    )
    op.create_index('ix_feedback_records_id', 'feedback_records', ['id'], unique=False)
    op.create_index('ix_feedback_records_employee_id', 'feedback_records', ['employee_id'], unique=True)
    op.create_index('ix_feedback_records_feedback_token', 'feedback_records', ['feedback_token'], unique=True)
    op.create_index('ix_feedback_records_status', 'feedback_records', ['status'], unique=False)

    # 2. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_employee_id', 'audit_logs', ['employee_id'], unique=False)
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'], unique=False)

    # 3. Seed Phase 3 Default System Settings
    settings_table = sa.table(
        'system_settings',
        sa.column('key', sa.String),
        sa.column('value', sa.String),
        sa.column('description', sa.String),
        sa.column('updated_at', sa.DateTime)
    )

    now = datetime.utcnow()
    op.bulk_insert(settings_table, [
        {'key': 'reminders_enabled', 'value': 'true', 'description': 'Enable Automatic Reminder Dispatches', 'updated_at': now},
        {'key': 'reminder_count', 'value': '2', 'description': 'Number of Reminder Emails to Send', 'updated_at': now},
        {'key': 'reminder_interval_days', 'value': '7', 'description': 'Days Between Reminders', 'updated_at': now},
        {'key': 'feedback_expiry_days', 'value': '30', 'description': 'Days After Creation Token Expires', 'updated_at': now},
        {'key': 'feedback_base_url', 'value': 'http://localhost:5173', 'description': 'Base URL for Public Feedback Link', 'updated_at': now},
    ])

    # 4. Seed Default Reminder Email Templates
    templates_table = sa.table(
        'email_templates',
        sa.column('template_key', sa.String),
        sa.column('subject', sa.String),
        sa.column('body', sa.String),
        sa.column('version', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )

    op.bulk_insert(templates_table, [
        {
            'template_key': 'EXIT_FEEDBACK_REMINDER_1',
            'subject': 'Reminder: Complete Your Employee Exit Feedback',
            'body': '''<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Reminder: We Value Your Feedback</h2>
<p>Dear {{employee_name}},</p>
<p>This is a friendly reminder to complete your employee exit feedback questionnaire for <strong>{{company_name}}</strong>.</p>
<p>Your honest insights help us continuously improve our workplace environment and culture for current and future team members.</p>
<p style="margin: 25px 0;">
  <a href="{{feedback_form_url}}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Complete Feedback Questionnaire &rarr;</a>
</p>
<p>If you have already submitted your feedback, please disregard this email.</p>
<p>Best regards,<br><strong>HR Department</strong><br>{{company_name}}</p>
</div>''',
            'version': '1.0',
            'is_active': True,
            'created_at': now,
            'updated_at': now
        },
        {
            'template_key': 'EXIT_FEEDBACK_REMINDER_2',
            'subject': 'Final Reminder: Your Exit Feedback Questionnaire',
            'body': '''<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Final Reminder: Exit Feedback Questionnaire</h2>
<p>Dear {{employee_name}},</p>
<p>We haven't received your exit feedback questionnaire yet. Your input is extremely valuable to <strong>{{company_name}}</strong>.</p>
<p>Please take a few moments to share your experience with us before your link expires.</p>
<p style="margin: 25px 0;">
  <a href="{{feedback_form_url}}" style="background-color: #059669; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Submit Your Feedback Now &rarr;</a>
</p>
<p>Thank you for your contributions and time!</p>
<p>Best regards,<br><strong>HR Department</strong><br>{{company_name}}</p>
</div>''',
            'version': '1.0',
            'is_active': True,
            'created_at': now,
            'updated_at': now
        }
    ])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('feedback_records')
