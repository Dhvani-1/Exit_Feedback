from typing import Dict, Any
from jinja2.sandbox import SandboxedEnvironment


# Sandboxed environment restricting template execution to safe variable access
env = SandboxedEnvironment(autoescape=True)


def render_email_template(template_str: str, context: Dict[str, Any]) -> str:
    """
    Renders an HTML email template safely using Jinja2 SandboxedEnvironment.
    
    Allowed context keys:
    - employee_name
    - employee_id
    - last_working_date
    - feedback_due_date
    - feedback_form_url
    - company_name
    """
    template = env.from_string(template_str)
    
    # Filter context to permitted keys only for security
    allowed_keys = {
        "employee_name",
        "employee_id",
        "last_working_date",
        "feedback_due_date",
        "feedback_form_url",
        "company_name",
        "designation",
        "start_date",
        "tenure",
    }
    safe_context = {k: v for k, v in context.items() if k in allowed_keys}
    
    return template.render(**safe_context)
