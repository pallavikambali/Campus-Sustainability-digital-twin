import logging
import smtplib
import ssl
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Incident, NotificationDelivery, SensorReading, Zone
from app.read_repository import list_active_incidents

logger = logging.getLogger(__name__)


def _send_email(incident: Incident, zone: Zone, reading: SensorReading | None) -> None:
    if not settings.email_alerts_configured:
        raise RuntimeError("Email notifications are not configured")

    message = EmailMessage()
    message["Subject"] = f"Critical campus incident: {zone.name} — {incident.type}"
    message["From"] = settings.smtp_from_email
    message["To"] = settings.critical_alert_recipient

    details = [
        f"Incident: {incident.type}",
        f"Zone: {zone.name}",
        f"Severity: {incident.severity}",
        f"Status: {incident.status}",
        f"Detected at: {incident.created_at.isoformat()}",
        f"Description: {incident.description}",
    ]
    if incident.current_value is not None:
        details.append(f"Incident reading: {incident.current_value}")
    if incident.expected_range:
        details.append(f"Expected range: {incident.expected_range}")
    if reading is not None:
        details.extend(
            [
                f"Latest sensor reading at: {reading.timestamp.isoformat()}",
                f"Energy: {reading.energy_kwh} kWh",
                f"Water: {reading.water_liters} L",
                f"Occupancy: {reading.occupancy} / capacity {zone.capacity}",
            ]
        )
    message.set_content("\n".join(details))

    context = ssl.create_default_context()
    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
            context=context,
        ) as server:
            if settings.smtp_username and settings.smtp_password:
                server.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
            server.send_message(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls(context=context)
        if settings.smtp_username and settings.smtp_password:
            server.login(
                settings.smtp_username,
                settings.smtp_password.get_secret_value(),
            )
        server.send_message(message)


def notify_critical_zone(session: Session, zone_id: UUID) -> None:
    """Send at most one email attempt for each active incident in a critical zone."""
    if not settings.email_alerts_configured:
        return

    try:
        with session.begin():
            zone = session.get(Zone, zone_id)
            if zone is None or zone.status != "CRITICAL":
                return

            latest_reading = session.scalar(
                select(SensorReading)
                .where(SensorReading.zone_id == zone_id)
                .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
                .limit(1)
            )

            for incident in list_active_incidents(session, zone_id):
                if incident.severity not in {"HIGH", "CRITICAL"}:
                    continue
                already_attempted = session.scalar(
                    select(NotificationDelivery.id).where(
                        NotificationDelivery.incident_id == incident.id,
                        NotificationDelivery.channel == "EMAIL",
                    )
                )
                if already_attempted:
                    continue

                delivery = NotificationDelivery(
                    incident_id=incident.id,
                    channel="EMAIL",
                    status="FAILED",
                )
                session.add(delivery)
                session.flush()
                try:
                    _send_email(incident, zone, latest_reading)
                except Exception as error:
                    delivery.status = "FAILED"
                    delivery.error = str(error)[:1000]
                    logger.warning(
                        "Critical incident email failed for incident %s: %s",
                        incident.id,
                        error,
                    )
                else:
                    # SMTP acceptance is not proof that the recipient's inbox
                    # received or displayed the message.
                    delivery.status = "ACCEPTED"
                    delivery.error = None
    except IntegrityError:
        # The database uniqueness constraint is the final deduplication guard
        # if two workers try to notify for the same incident concurrently.
        session.rollback()
