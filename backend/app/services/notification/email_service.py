import logging
from typing import List, Optional
from jinja2 import Environment, PackageLoader, select_autoescape
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

from app.core.config import Settings as settings


logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.SMTP_FROM,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_SERVER,
    MAIL_TLS=settings.SMTP_TLS,
    MAIL_SSL=settings.SMTP_SSL,
    USE_CREDENTIALS=True,
)

jinja = Environment(
    loader=PackageLoader("app.services.notification", "templates"),
    autoescape=select_autoescape(["html", "xml"])
)

class EmailService:
    """Service for sending templated emails."""

    def __init__(self):
        self.fm = FastMail(conf)

    async def send_email(
        self,
        subject: str,
        recipients: List[str],
        template_name: str,
        context: dict,
        attachments: Optional[List] = None
    ) -> None:
        html_body = jinja.get_template(template_name).render(**context)
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html_body,
            subtype="html"
        )
        try:
            await self.fm.send_message(message, template_name=None, attachments=attachments)
            logger.info(f"Email sent to {recipients}, subject: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipients}: {e}")
            raise
