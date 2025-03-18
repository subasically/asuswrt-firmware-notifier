import os
import json
import requests
import time
import feedparser
from logger import logger  # new logger import
import shutil  # added for directory removal

# Retrieve environment variables
rss_feed_url = os.environ.get("RSS_FEED_URL")
last_version_file = os.environ.get("LAST_VERSION_FILE", "last_version.txt")
notification_method = os.environ.get("NOTIFICATION_METHOD")
email_address = os.environ.get("EMAIL_ADDRESS")
slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
check_frequency = int(os.environ.get("CHECK_FREQUENCY", 60))

# App Intro Logging
logger.info(
    """
    ╔════════════════════════════════════════════════════════╗
    ║    Asuswrt-Merlin Firmware Notifier is now running!     ║
    ║       Monitoring for the latest firmware updates.       ║
    ╚════════════════════════════════════════════════════════╝
"""
)

logger.info(f"RSS Feed URL: {rss_feed_url}")
logger.info(f"Last Version File: {last_version_file}")
logger.info(f"Notification Method: {notification_method}")
logger.info(f"Email Address: {email_address}")
logger.info(f"Slack Webhook URL: {slack_webhook_url}")
logger.info(f"Check Frequency: {check_frequency}")

# Ensure the last_version file exists
if not os.path.exists(last_version_file):
    with open(last_version_file, "w") as f:
        f.write("")


def get_last_version(file_path):
    """Reads the last known version from a file."""
    if os.path.isdir(file_path):
        logger.error(f"Error: Expected a file but found a directory at {file_path}.")
        return None  # Or handle appropriately
    try:
        with open(file_path, "r") as f:
            version = f.read().strip()
            if not version:  # Treat empty file as no version
                return None
            return version
    except FileNotFoundError:
        return None


def save_last_version(file_path, version):
    """Saves the latest version to a file."""
    if os.path.isdir(file_path):
        logger.warning(
            f"{file_path} is a directory. Removing directory and creating a file instead."
        )
        shutil.rmtree(file_path)
    with open(file_path, "w") as f:
        f.write(version)


def extract_version(item):
    """Extracts the firmware version from the RSS item title."""
    title = item.title
    try:
        version = title.split("_")[2] + "_" + title.split("_")[3]
        return version
    except IndexError:
        logger.warning(f"Warning: Could not extract version from title: {title}")
        return None


def validate_email(email):
    """Basic email validation."""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_slack_webhook(webhook_url):
    """Validates Slack webhook URL format."""
    if webhook_url.startswith("https://hooks.slack.com/services/"):
        return True
    return False


def notify(message):
    """Sends a notification based on the configured method."""
    if notification_method == "print":
        logger.info(message)
    elif (
        notification_method == "email"
        and email_address
        and validate_email(email_address)
    ):
        send_email(email_address, "New Asuswrt-Merlin Firmware Available", message)
    elif (
        notification_method == "slack"
        and slack_webhook_url
        and validate_slack_webhook(slack_webhook_url)
    ):
        send_slack(slack_webhook_url, message)
    else:
        logger.warning(
            f"Warning: Unknown notification method or invalid credentials: {notification_method}"
        )


def send_email(to_address, subject, body):
    """Sends an email notification (requires an email library like smtplib)."""
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "asuswrt-merlin-notifier@example.com"  # Change this
    msg["To"] = to_address
    try:
        with smtplib.SMTP(
            "smtp.example.com", 587
        ) as server:  # Replace with your SMTP server
            server.starttls()  # Secure the connection
            server.login(
                "your_username", "your_password"
            )  # Replace with your credentials
            server.sendmail(
                "asuswrt-merlin-notifier@example.com", to_address, msg.as_string()
            )
        logger.info("Email sent successfully!")
    except Exception as e:
        logger.error(f"Error sending email: {e}")


def send_slack(webhook_url, message):
    """Sends a message to a Slack channel."""
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps({"text": message}),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        logger.info("Message sent to Slack successfully!")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message to Slack: {e}")


def main():
    """Main function to check for firmware updates and notify."""
    try:
        feed = feedparser.parse(rss_feed_url)
        if feed.entries:
            latest_entry = feed.entries[0]
            latest_version = extract_version(latest_entry)
            if latest_version:
                last_version = get_last_version(last_version_file)
                if last_version is None or latest_version > last_version:
                    message = f"New Asuswrt-Merlin firmware available!\nVersion: {latest_version}\nDownload link: {latest_entry.link}"
                    notify(message)
                    save_last_version(last_version_file, latest_version)
                    logger.info(f"Notified about new version: {latest_version}")
                else:
                    logger.info(
                        f"No new firmware found. Current version: {last_version}, Latest version: {latest_version}"
                    )
            else:
                logger.error("Error: Could not extract version from RSS entry.")
        else:
            logger.error("Error: Could not retrieve RSS feed.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

    time.sleep(check_frequency * 5)  # Check every 5 minutes. Adjust as needed.


if __name__ == "__main__":
    main()
