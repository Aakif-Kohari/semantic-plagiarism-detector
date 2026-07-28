"""
daily_summary_email.py
----------------------
Scheduled task to aggregate daily plagiarism incidents and send a summary email to administrators.
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


def format_daily_summary(incidents: List[Dict[str, Any]]) -> str:
    """
    Format incidents into a readable HTML email summary.

    Args:
        incidents: List of incident dictionaries

    Returns:
        HTML formatted email body
    """
    if not incidents:
        return """
        <html>
        <body>
            <h2>Daily Plagiarism Summary</h2>
            <p>No new plagiarism incidents detected in the last 24 hours.</p>
        </body>
        </html>
        """

    # Group by severity
    high_severity = [inc for inc in incidents if inc.get("severity_rank") == "High"]
    medium_severity = [inc for inc in incidents if inc.get("severity_rank") == "Medium"]
    low_severity = [inc for inc in incidents if inc.get("severity_rank") == "Low"]

    html = f"""
    <html>
    <body>
        <h2>Daily Plagiarism Summary</h2>
        <p>Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p>Total new incidents: {len(incidents)}</p>

        <h3>Severity Breakdown:</h3>
        <ul>
            <li><strong>High:</strong> {len(high_severity)}</li>
            <li><strong>Medium:</strong> {len(medium_severity)}</li>
            <li><strong>Low:</strong> {len(low_severity)}</li>
        </ul>

        <h3>High Severity Incidents:</h3>
    """

    if high_severity:
        html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
        html += "<tr><th>Document A</th><th>Document B</th><th>Similarity</th><th>Date Flagged</th></tr>"
        for inc in high_severity:
            html += f"""
            <tr>
                <td>{inc.get('document_a', '')}</td>
                <td>{inc.get('document_b', '')}</td>
                <td>{inc.get('similarity_score', 0):.2%}</td>
                <td>{inc.get('date_flagged', '')}</td>
            </tr>
            """
        html += "</table>"
    else:
        html += "<p>No high severity incidents.</p>"

    html += """
        <h3>Medium Severity Incidents:</h3>
    """

    if medium_severity:
        html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
        html += "<tr><th>Document A</th><th>Document B</th><th>Similarity</th><th>Date Flagged</th></tr>"
        for inc in medium_severity:
            html += f"""
            <tr>
                <td>{inc.get('document_a', '')}</td>
                <td>{inc.get('document_b', '')}</td>
                <td>{inc.get('similarity_score', 0):.2%}</td>
                <td>{inc.get('date_flagged', '')}</td>
            </tr>
            """
        html += "</table>"
    else:
        html += "<p>No medium severity incidents.</p>"

    base_url = os.getenv("APP_BASE_URL", "http://localhost:8501")
    html += f"""
        <p><em>Review all incidents in the dashboard: <a href="{base_url}">{base_url}</a></em></p>
    </body>
    </html>
    """

    return html


def send_email(to_emails: List[str], subject: str, html_body: str) -> bool:
    """
    Send an email using SMTP.

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

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        logger.info(
            f"Daily summary email sent successfully to {len(to_emails)} recipients"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send daily summary email: {e}")
        return False


def send_daily_summary() -> bool:
    """
    Main function to aggregate daily incidents and send summary email.

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

    # Format the summary
    html_body = format_daily_summary(incidents)

    # Send the email
    subject = f"Daily Plagiarism Summary - {datetime.now().strftime('%Y-%m-%d')}"
    success = send_email(admin_emails, subject, html_body)

    return success


if __name__ == "__main__":
    success = send_daily_summary()
    exit(0 if success else 1)
