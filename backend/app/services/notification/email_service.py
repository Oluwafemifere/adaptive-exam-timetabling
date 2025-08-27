# app/services/notification/email_service.py
import logging
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

from jinja2 import Environment, PackageLoader, select_autoescape
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from starlette.datastructures import UploadFile
from pydantic import SecretStr
from typing import cast

from app.core import Settings as settings

logger = logging.getLogger(__name__)

# Convert template folder path to Path object if it exists
template_folder: Optional[str] = getattr(settings, "MAIL_TEMPLATE_FOLDER", None)
template_folder_path: Optional[Path] = Path(template_folder) if template_folder else None

# Explicitly typed connection config
conf: ConnectionConfig = ConnectionConfig(
    MAIL_USERNAME=cast(str, SecretStr(settings.SMTP_USER or "")),
    MAIL_PASSWORD=SecretStr(settings.SMTP_PASSWORD or ""),
    MAIL_FROM=settings.SMTP_FROM or "noreply@example.com",
    MAIL_PORT=int(settings.SMTP_PORT or 587),
    MAIL_SERVER=settings.SMTP_SERVER or "localhost",
    MAIL_STARTTLS=bool(getattr(settings, "SMTP_STARTTLS", True)),
    MAIL_SSL_TLS=bool(getattr(settings, "SMTP_SSL_TLS", False)),
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=template_folder_path,
)

# Jinja2 environment
jinja: Environment = Environment(
    loader=PackageLoader("app.services.notification", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailService:
    """Service for sending templated emails."""

    def __init__(self) -> None:
        self.fm: FastMail = FastMail(conf)

    async def send_email(
        self,
        subject: str,
        recipients: List[str],
        template_name: str,
        context: Dict[str, Any],
        attachments: Optional[List[Union[UploadFile, dict, str]]] = None,
    ) -> None:
        html_body: str = jinja.get_template(template_name).render(**context)

        message: MessageSchema = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html_body,
            subtype=MessageType.html,
            attachments=attachments or [],
        )

        try:
            await self.fm.send_message(message)
            logger.info("Email sent to %s subject=%s", recipients, subject)
        except Exception as e:
            logger.exception("Failed to send email to %s: %s", recipients, e)
            raise
