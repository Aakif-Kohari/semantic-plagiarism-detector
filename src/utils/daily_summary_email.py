"""
daily_summary_email.py
----------------------
Scheduled task to aggregate daily plagiarism incidents and send a summary email to administrators.
Features modular, inline-CSS styled HTML template generation for maximum email client compatibility.
"""

import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.db.auth import get_all_users
from src.db.incidents import DEFAULT_DB_PATH, get_all_incidents

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_incidents_last_24h(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieve all incidents flagged in the last 24 hours.

    Args:
        db_path: Path to the SQLite database

    Returns:
        List of incident dictionaries
    """
    cutoff_time = (
        (datetime.now(timezone.utc) - timedelta(hours=24))
        .replace(microsecond=0)
        .isoformat()
    )

    all_incidents = get_all_incidents(db_path)
    recent_incidents = [
        inc for inc in all_incidents if inc.get("date_flagged", "") >= cutoff_time
    ]

    return recent_incidents


def get_admin_emails() -> List[str]:
    """
    Retrieve email addresses for all admin users.

    Returns:
        List of admin email addresses
    """
    users = get_all_users()
    admin_emails = []

    for user in users:
        if user.get("role") == "admin":
            # For now, use username as email. In production, you'd want an email field in the users table
            admin_emails.append(f"{user['username']}@localhost")

    # Fallback to environment variable if no admins found
    if not admin_emails:
        env_email = os.getenv("ADMIN_EMAIL")
        if env_email:
            admin_emails.append(env_email)

    return admin_emails


def build_incident_row_html(inc: Dict[str, Any]) -> str:
    """
    Build a single HTML table row for an incident.

    Args:
        inc: Dictionary containing incident data.

    Returns:
        str: HTML <tr> element with inline styles.
    """
    doc_a = inc.get("document_a", "Unknown")
    doc_b = inc.get("document_b", "Unknown")
    similarity = inc.get("similarity_score", 0.0)
    date_flagged = inc.get("date_flagged", "Unknown")

    return f"""
    <tr>
        <td style="padding: 12px; border-bottom: 1px solid #eeeeee; color: #333333;">{doc_a}</td>
        <td style="padding: 12px; border-bottom: 1px solid #eeeeee; color: #333333;">{doc_b}</td>
        <td style="padding: 12px; border-bottom: 1px solid #eeeeee; color: #333333; font-weight: bold;">{similarity:.2%}</td>
        <td style="padding: 12px; border-bottom: 1px solid #eeeeee; color: #666666;">{date_flagged}</td>
    </tr>
    """


def build_severity_section_html(severity: str, incidents: List[Dict[str, Any]]) -> str:
    """
    Build an HTML section for a specific severity level.

    Args:
        severity: The severity level (e.g., "High", "Medium", "Low").
        incidents: List of incidents matching this severity.

    Returns:
        str: HTML section with a table of incidents.
    """
    color_map = {
        "High": "#d32f2f",
        "Medium": "#f57c00",
        "Low": "#388e3c",
    }
    color = color_map.get(severity, "#666666")

    html = f"""
    <h3 style="color: {color}; margin-top: 24px; margin-bottom: 12px; font-size: 18px; border-bottom: 2px solid {color}; padding-bottom: 4px;">
        {severity} Severity Incidents ({len(incidents)})
    </h3>
    """

    if not incidents:
        html += f'<p style="color: #666666; font-style: italic;">No {severity.lower()} severity incidents detected.</p>'
        return html

    html += """
    <table style="width: 100%; border-collapse: collapse; margin-top: 8px; background-color: #ffffff; border-radius: 4px; overflow: hidden;">
        <thead>
            <tr style="background-color: #f5f5f5;">
                <th style="padding: 12px; text-align: left; color: #333333; font-weight: 600; border-bottom: 2px solid #dddddd;">Document A</th>
                <th style="padding: 12px; text-align: left; color: #333333; font-weight: 600; border-bottom: 2px solid #dddddd;">Document B</th>
                <th style="padding: 12px; text-align: left; color: #333333; font-weight: 600; border-bottom: 2px solid #dddddd;">Similarity</th>
                <th style="padding: 12px; text-align: left; color: #333333; font-weight: 600; border-bottom: 2px solid #dddddd;">Date Flagged</th>
            </tr>
        </thead>
        <tbody>
    """

    for inc in incidents:
        html += build_incident_row_html(inc)

    html += "</tbody></table>"
    return html


def build_email_html_body(
    incidents_data: List[Dict[str, Any]], total_scans: int
) -> str:
    """
    Build a clean, inline-CSS styled HTML email body for the daily summary.

    This function extracts the template logic to improve email customization
    and ensure compatibility with various email clients (Gmail, Outlook, etc.)
    by using inline CSS styling.

    Args:
        incidents_data: List of incident dictionaries.
        total_scans: Total number of scans performed in the period.

    Returns:
        str: The fully formatted HTML email body.
    """
    if not incidents_data:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
            <h2 style="color: #333333; text-align: center;">Daily Plagiarism Summary</h2>
            <p style="color: #666666; text-align: center; font-size: 16px;">
                No new plagiarism incidents detected in the last 24 hours.
            </p>
            <p style="color: #888888; text-align: center; font-size: 14px; margin-top: 40px;">
                Total scans processed: <strong>{total_scans}</strong>
            </p>
        </div>
        """

    high_severity = [
        inc for inc in incidents_data if inc.get("severity_rank") == "High"
    ]
    medium_severity = [
        inc for inc in incidents_data if inc.get("severity_rank") == "Medium"
    ]
    low_severity = [inc for inc in incidents_data if inc.get("severity_rank") == "Low"]

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
        <h2 style="color: #333333; text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Daily Plagiarism Summary</h2>
        <p style="color: #666666; font-size: 14px; text-align: right;">
            Report generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
        </p>
        
        <div style="background-color: #ffffff; padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <p style="font-size: 16px; color: #333333; margin-bottom: 20px;">
                <strong>Total new incidents:</strong> {len(incidents_data)}<br>
                <strong>Total scans processed:</strong> {total_scans}
            </p>
            
            <p style="font-size: 14px; color: #666666; margin-bottom: 20px;">
                <strong>Severity Breakdown:</strong><br>
                🔴 High: {len(high_severity)} | 🟡 Medium: {len(medium_severity)} | 🟢 Low: {len(low_severity)}
            </p>
            
            {build_severity_section_html("High", high_severity)}
            {build_severity_section_html("Medium", medium_severity)}
            {build_severity_section_html("Low", low_severity)}
        </div>
        
        <p style="color: #888888; text-align: center; font-size: 14px; margin-top: 30px;">
            <a href="{os.getenv('APP_BASE_URL', 'http://localhost:8501')}" style="color: #007bff; text-decoration: none;">Review all incidents in the dashboard</a>
        </p>
    </div>
    """
    return html


def format_daily_summary(incidents: List[Dict[str, Any]]) -> str:
    """
    Legacy wrapper for backward compatibility.
    Delegates to the new build_email_html_body function.
    """
    return build_email_html_body(incidents_data=incidents, total_scans=0)


def send_email(to_emails: List[str], subject: str, html_body: str) -> bool:
    """
    Send an email using SMTP.

    The connection method is chosen automatically based on ``SMTP_PORT``:

    * **Port 465** – uses :class:`smtplib.SMTP_SSL` (implicit SSL).
    * **Any other port** (default: 587) – uses :class:`smtplib.SMTP` with
      ``STARTTLS`` upgrade.

    Args:
        to_emails: List of recipient email addresses
        subject: Email subject line
        html_body: HTML formatted email body

    Returns:
        True if email sent successfully, False otherwise
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL", smtp_username)

    if not all([smtp_server, smtp_username, smtp_password]):
        logger.error(
            "SMTP configuration incomplete. Please set SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD."
        )
        return False

    if not to_emails:
        logger.warning("No recipients configured for daily summary email.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = ", ".join(to_emails)

        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Port 465 uses implicit SSL; all other ports use STARTTLS.
        if smtp_port == 465:
            logger.debug("Using SMTP_SSL (implicit SSL) on port %d", smtp_port)
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        else:
            logger.debug("Using SMTP with STARTTLS on port %d", smtp_port)
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)

        logger.info(
            "Daily summary email sent successfully to %d recipients", len(to_emails)
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send daily summary email: {e}")
        return False


def send_daily_summary(subject_prefix: str = "[Plagiarism Alert]") -> bool:
    """
    Main function to aggregate daily incidents and send summary email.

    Args:
        subject_prefix: Prefix to prepend to the email subject line

    Returns:
        True if email sent successfully, False otherwise
    """
    logger.info("Starting daily summary email generation...")

    # Get incidents from last 24 hours
    incidents = get_incidents_last_24h()
    logger.info(f"Found {len(incidents)} incidents in the last 24 hours")

    # Get admin email addresses
    admin_emails = get_admin_emails()
    logger.info(f"Sending to {len(admin_emails)} admin recipients")

    # Format the summary using the new inline HTML builder
    html_body = build_email_html_body(incidents_data=incidents, total_scans=100)

    # Send the email
    prefix = f"{subject_prefix} " if subject_prefix else ""
    subject = f"{prefix}Daily Plagiarism Summary - {datetime.now().strftime('%Y-%m-%d')}"
    success = send_email(admin_emails, subject, html_body)

    return success


if __name__ == "__main__":
    success = send_daily_summary()
    exit(0 if success else 1)
