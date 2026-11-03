"""Deliver a notification to a student: browser push, email, or both.

Two channels because neither reaches everyone. Push is instant and free but
an iPhone only receives it once the student has added StudyMate to the home
screen; email reaches every student but is easier to miss.
"""

import json
import logging
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from email.message import EmailMessage
from html import escape

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.schedule import PushSubscription
from app.models.user import User

logger = logging.getLogger(__name__)

# The push service answers 404/410 for a subscription that no longer exists
# (the student cleared site data, uninstalled, revoked permission).
_GONE = (404, 410)


@dataclass(frozen=True)
class Notification:
    title: str
    body: str
    # Path inside the app to open when the notification is tapped.
    path: str = "/"
    # Notifications with the same tag replace each other on the device rather
    # than stacking, so a lecture never shows three separate reminders at once.
    tag: str = "studymate"

    @property
    def url(self) -> str:
        return f"{settings.app_url.rstrip('/')}{self.path}"


def send_push(db: Session, student_id: uuid.UUID, note: Notification) -> int:
    """Push to every device the student has subscribed. Returns how many succeeded."""
    if not settings.push_enabled:
        return 0

    from pywebpush import WebPushException, webpush

    payload = json.dumps({"title": note.title, "body": note.body, "url": note.path, "tag": note.tag})
    delivered = 0
    for subscription in db.query(PushSubscription).filter(PushSubscription.student_id == student_id).all():
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
                ttl=3600,
            )
            delivered += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in _GONE:
                db.delete(subscription)
            else:
                logger.warning("Push to %s failed: %s", subscription.endpoint[:60], exc)
    db.commit()
    return delivered


def _email_html(note: Notification) -> str:
    return f"""\
<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:auto;padding:24px;color:#0A1F44">
  <p style="font-size:13px;font-weight:700;color:#A9862B;margin:0 0 12px">StudyMate</p>
  <h1 style="font-size:20px;margin:0 0 8px">{escape(note.title)}</h1>
  <p style="font-size:15px;line-height:1.5;margin:0 0 20px;color:#334">{escape(note.body)}</p>
  <a href="{escape(note.url)}" style="display:inline-block;background:#0A1F44;color:#D4AF37;padding:10px 18px;border-radius:8px;font-weight:600;text-decoration:none">Open StudyMate</a>
  <p style="font-size:12px;color:#889;margin-top:24px">You can turn these emails off in your StudyMate profile.</p>
</div>"""


def send_email(user: User, note: Notification) -> bool:
    if not settings.email_enabled:
        return False

    message = EmailMessage()
    message["Subject"] = note.title
    message["From"] = settings.email_from
    message["To"] = user.email
    message.set_content(f"{note.body}\n\n{note.url}\n\nTurn these emails off in your StudyMate profile.")
    message.add_alternative(_email_html(note), subtype="html")

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=20) as smtp:
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Email to %s failed: %s", user.email, exc)
        return False


def notify(db: Session, user: User, note: Notification) -> dict[str, int | bool]:
    """Send on every channel the student has left switched on."""
    pushed = send_push(db, user.id, note) if user.notify_push else 0
    emailed = send_email(user, note) if user.notify_email else False
    return {"push": pushed, "email": emailed}
