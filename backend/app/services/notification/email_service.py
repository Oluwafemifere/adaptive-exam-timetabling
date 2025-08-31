# backend/app/services/notification/email_service.py

"""
Email service for sending templated emails with proper error handling,
retry logic, and configuration management.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import ssl
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration container"""

    smtp_server: str
    smtp_port: int
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "noreply@example.com"
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30


@dataclass
class EmailMessage:
    """Email message container"""

    subject: str
    recipients: List[str]
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


class EmailService:
    """Service for sending templated emails with robust error handling."""

    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or self._load_config_from_settings()
        self._template_cache: Dict[str, str] = {}

    def _load_config_from_settings(self) -> EmailConfig:
        """Load email configuration from settings"""
        try:
            from app.core.config import settings

            return EmailConfig(
                smtp_server=getattr(settings, "SMTP_SERVER", "localhost"),
                smtp_port=getattr(settings, "SMTP_PORT", 587),
                smtp_user=getattr(settings, "SMTP_USER", ""),
                smtp_password=getattr(settings, "SMTP_PASSWORD", ""),
                smtp_from=getattr(settings, "SMTP_FROM", "noreply@example.com"),
                use_tls=getattr(settings, "SMTP_STARTTLS", True),
                use_ssl=getattr(settings, "SMTP_SSL_TLS", False),
            )
        except Exception as e:
            logger.warning(f"Failed to load email settings: {e}")
            return EmailConfig(
                smtp_server="localhost",
                smtp_port=587,
                smtp_user="",
                smtp_password="",
                smtp_from="noreply@example.com",
            )

    async def send_email(
        self,
        subject: str,
        recipients: List[str],
        template_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        retry_count: int = 3,
    ) -> bool:
        """
        Send email with template rendering or direct content.

        Args:
            subject: Email subject
            recipients: List of recipient email addresses
            template_name: Name of template to render (optional)
            context: Template context variables (optional)
            html_body: Direct HTML content (optional)
            text_body: Direct text content (optional)
            attachments: List of attachments (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            retry_count: Number of retry attempts

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Validate input
            if not recipients:
                logger.error("No recipients provided")
                return False

            if not subject:
                logger.error("No subject provided")
                return False

            # Prepare email content
            if template_name and context:
                html_body = await self._render_template(template_name, context)
                if not html_body:
                    logger.error(f"Failed to render template: {template_name}")
                    return False

            if not html_body and not text_body:
                logger.error("No email content provided")
                return False

            # Create email message
            message = EmailMessage(
                subject=subject,
                recipients=recipients,
                html_body=html_body,
                text_body=text_body,
                attachments=attachments or [],
                cc=cc,
                bcc=bcc,
            )

            # Send with retry logic
            for attempt in range(retry_count):
                try:
                    success = await self._send_message(message)
                    if success:
                        logger.info(f"Email sent successfully to {recipients}")
                        return True
                except Exception as e:
                    logger.warning(f"Email send attempt {attempt + 1} failed: {e}")
                    if attempt == retry_count - 1:
                        logger.error(
                            f"Failed to send email after {retry_count} attempts"
                        )
                        return False
                    await asyncio.sleep(2**attempt)  # Exponential backoff

            return False

        except Exception as e:
            logger.error(f"Email service error: {e}", exc_info=True)
            return False

    async def _render_template(
        self, template_name: str, context: Dict[str, Any]
    ) -> Optional[str]:
        """Render email template with context"""
        try:
            # Try to load template from cache
            if template_name in self._template_cache:
                template_content = self._template_cache[template_name]
            else:
                # Load template from file
                template_content = await self._load_template(template_name)  # type: ignore
                if template_content:
                    self._template_cache[template_name] = template_content
                else:
                    return None

            # Handle case where template_content might be None
            if template_content is None:
                return None

            # Simple template rendering (in production, use Jinja2 or similar)
            rendered = template_content
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}"
                rendered = rendered.replace(placeholder, str(value))

            return rendered

        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return None

    async def _load_template(self, template_name: str) -> Optional[str]:
        """Load template from file system"""
        try:
            # Look for template in various locations
            template_paths = [
                Path("app/services/notification/templates") / f"{template_name}.html",
                Path("templates") / f"{template_name}.html",
                Path(f"{template_name}.html"),
            ]

            for template_path in template_paths:
                if template_path.exists():
                    with open(template_path, "r", encoding="utf-8") as f:
                        return f.read()

            logger.warning(f"Template not found: {template_name}")
            return None

        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            return None

    async def _send_message(self, message: EmailMessage) -> bool:
        """Send email message via SMTP"""
        try:
            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = self.config.smtp_from
            msg["To"] = ", ".join(message.recipients)

            if message.cc:
                msg["Cc"] = ", ".join(message.cc)

            # Add text and HTML parts
            if message.text_body:
                text_part = MIMEText(message.text_body, "plain", "utf-8")
                msg.attach(text_part)

            if message.html_body:
                html_part = MIMEText(message.html_body, "html", "utf-8")
                msg.attach(html_part)

            # Add attachments
            if message.attachments:
                for attachment in message.attachments:
                    await self._add_attachment(msg, attachment)

            # Prepare recipient list
            all_recipients = message.recipients.copy()
            if message.cc:
                all_recipients.extend(message.cc)
            if message.bcc:
                all_recipients.extend(message.bcc)

            # Send email
            await self._send_via_smtp(msg, all_recipients)
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def _add_attachment(
        self, msg: MIMEMultipart, attachment: Dict[str, Any]
    ) -> None:
        """Add attachment to email message"""
        try:
            filename = attachment.get("filename", "attachment")
            content = attachment.get("content", b"")

            # Create attachment part
            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )
            msg.attach(part)

        except Exception as e:
            logger.error(
                f"Failed to add attachment {attachment.get('filename', 'unknown')}: {e}"
            )

    async def _send_via_smtp(self, msg: MIMEMultipart, recipients: List[str]) -> None:
        """Send email via SMTP server"""

        def _send_sync():
            # Create SMTP connection
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout,
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout,
                )

            try:
                if self.config.use_tls and not self.config.use_ssl:
                    server.starttls(context=ssl.create_default_context())

                # Authenticate if credentials provided
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)

                # Send email
                server.send_message(msg, to_addrs=recipients)

            finally:
                server.quit()

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_sync)

    async def send_job_notification(
        self,
        user_email: str,
        job_id: str,
        status: str,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send job status notification email"""

        subject_map = {
            "completed": "Timetable Generation Completed",
            "failed": "Timetable Generation Failed",
            "cancelled": "Timetable Generation Cancelled",
        }

        subject = subject_map.get(status, f"Timetable Job Update - {status.title()}")

        # Create simple HTML content
        html_body = f"""
        <html>
        <body>
            <h2>{subject}</h2>
            <p>Your timetable generation job (ID: {job_id}) has {status}.</p>
            {self._format_additional_info(additional_info)}
            <p>You can check the full details in your dashboard.</p>
            <p>Best regards,<br>Exam Timetabling System</p>
        </body>
        </html>
        """

        text_body = f"""
        {subject}
        
        Your timetable generation job (ID: {job_id}) has {status}.
        
        You can check the full details in your dashboard.
        
        Best regards,
        Exam Timetabling System
        """

        return await self.send_email(
            subject=subject,
            recipients=[user_email],
            html_body=html_body,
            text_body=text_body,
        )

    def _format_additional_info(self, info: Optional[Dict[str, Any]]) -> str:
        """Format additional information for email"""
        if not info:
            return ""

        html = "<ul>"
        for key, value in info.items():
            html += f"<li><strong>{key.title()}:</strong> {value}</li>"
        html += "</ul>"

        return html

    async def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:

            def _test_sync():
                if self.config.use_ssl:
                    server = smtplib.SMTP_SSL(
                        self.config.smtp_server, self.config.smtp_port, timeout=10
                    )
                else:
                    server = smtplib.SMTP(
                        self.config.smtp_server, self.config.smtp_port, timeout=10
                    )

                try:
                    if self.config.use_tls and not self.config.use_ssl:
                        server.starttls(context=ssl.create_default_context())

                    if self.config.smtp_user and self.config.smtp_password:
                        server.login(self.config.smtp_user, self.config.smtp_password)

                    return True
                finally:
                    server.quit()

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _test_sync)

            if result:
                logger.info("SMTP connection test successful")
            else:
                logger.error("SMTP connection test failed")

            return result

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
