import os
import json
import requests
import time
import feedparser

# Retrieve environment variables
rss_feed_url = os.environ.get("RSS_FEED_URL")
last_version_file = os.environ.get("LAST_VERSION_FILE")
notification_method = os.environ.get("NOTIFICATION_METHOD")
email_address = os.environ.get("EMAIL_ADDRESS")
slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
check_frequency = int(os.environ.get("CHECK_FREQUENCY", 60))

print(f"RSS Feed URL: {rss_feed_url}")
print(f"Last Version File: {last_version_file}")
print(f"Notification Method: {notification_method}")
print(f"Email Address: {email_address}")
print(f"Slack Webhook URL: {slack_webhook_url}")
print(f"Check Frequency:", {check_frequency})

def get_last_version(file_path):
    """Reads the last known version from a file."""
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_version(file_path, version):
    """Saves the latest version to a file."""
    with open(file_path, "w") as f:
        f.write(version)

def extract_version(item):
    """Extracts the firmware version from the RSS item title."""
    title = item.title
    try:
        version = title.split('_')[2] + "_" + title.split('_')[3]
        return version
    except IndexError:
        print(f"Warning: Could not extract version from title: {title}")
        return None

def validate_email(email):
    """Basic email validation."""
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def validate_slack_webhook(webhook_url):
    """Basic Slack webhook validation by sending a test message."""
    try:
        response = requests.post(webhook_url, data=json.dumps({"text": "Test message from firmware checker."}), headers={'Content-Type': 'application/json'})
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return True
    except requests.exceptions.RequestException:
        return False

def notify(message):
    """Sends a notification based on the configured method."""
    if notification_method == "print":
        print(message)
    elif notification_method == "email" and email_address and validate_email(email_address):
        send_email(email_address, "New Asuswrt-Merlin Firmware Available", message)
    elif notification_method == "slack" and slack_webhook_url and validate_slack_webhook(slack_webhook_url):
        send_slack(slack_webhook_url, message)
    else:
        print(f"Warning: Unknown notification method or invalid credentials: {notification_method}")

def send_email(to_address, subject, body):
    """Sends an email notification (requires an email library like smtplib)."""
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = "asuswrt-merlin-notifier@example.com"  # Change this
    msg['To'] = to_address
    try:
        with smtplib.SMTP('smtp.example.com', 587) as server:  # Replace with your SMTP server
            server.starttls()  # Secure the connection
            server.login("your_username", "your_password")  # Replace with your credentials
            server.sendmail("asuswrt-merlin-notifier@example.com", to_address, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_slack(webhook_url, message):
    """Sends a message to a Slack channel."""
    try:
        response = requests.post(webhook_url, data=json.dumps({"text": message}), headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print("Message sent to Slack successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Slack: {e}")

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
                    print(f"Notified about new version: {latest_version}")
                else:
                    print("No new firmware found.")
            else:
                print("Error: Could not extract version from RSS entry.")
        else:
            print("Error: Could not retrieve RSS feed.")
    except Exception as e:
        print(f"An error occurred: {e}")

    time.sleep(check_frequency * 5)  # Check every 5 minutes. Adjust as needed.

if __name__ == "__main__":
    main()