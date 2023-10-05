'''
news_scrapper
v.2023-10-02
'''
import json
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from src._drv_mongodb import MongoCnx

# Load variables from .env
load_dotenv()
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT')
# print("DEBUG - ", smtp_username, smtp_password, smtp_server, smtp_port) # noqa

files_path = "./report_data"
if not os.path.exists(files_path):
    os.makedirs(files_path)


def build_report_payload(start_publish_date=None):
    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")

    collection_name = "news"
    status = "summarized"

    # 1. List keywords to be matched
    collection = mongo_cnx.db["keywords"]
    keyword_list = collection.distinct("keyword", {"active": True})
    keyword_list = [item.strip('"') for item in keyword_list]
    print("DEBUG - ", keyword_list)

    # 2. Match and update document statuses
    matches = mongo_cnx.match_doc_with_keywords(
        collection_name, start_publish_date=start_publish_date, status=status, keyword_list=keyword_list)
    print("DEBUG - ", matches)

    mongo_cnx.update_collection("news", matches)

    # 3. Fetch documents with match to create email payload
    domain = None
    status = "matched"
    payload = mongo_cnx.get_doc_summary(collection_name=collection_name, domain=domain,
                                        start_publish_date=start_publish_date, status=status)

    if len(payload) > 0:
        print("INFO  - Last document _id:", payload[-1]["_id"], ", publish_date:", payload[-1]["publish_date"])

        for item in payload:
            if "publish_date" in item and isinstance(item["publish_date"], datetime):
                # Convert the datetime object to a string with the desired format
                item["publish_date"] = item["publish_date"].strftime("%m/%d/%Y")

            item["domain"] = item["domain"].replace("www.", "")

        with open(f"{files_path}/report_payload.json", "w", encoding="utf-8") as json_file:
            json.dump(payload, json_file)
        print(f"INFO  - Payload saved on \'{files_path}/email_payload.json\'.")

    else:
        print("INFO  - Exiting program. There is no articles that match given settings.")
        sys.exit()

    return payload


def send_email_report(report_payload_json, email_recipients, cc_recipients=None):
    # 4. Generate Jinja2 report template
    # Load the Jinja template
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('./templates/report_template.html')

    # Render the HTML with Jinja
    print("INFO  - Building e-mail Daily Newsfeed.")
    current_date = datetime.now().strftime("%m/%d/%Y")
    html_content = template.render(data=report_payload_json, current_date=current_date)
    # print("DEBUG - ", html_content)

    # Setup email parameters
    email_sender = smtp_username
    email_subject = f"13D Monitor Newsfeed on {current_date}"

    # Create the MIME message
    msg = MIMEMultipart()
    msg['From'] = email_sender
    msg['To'] = ', '.join(email_recipients)
    msg['Cc'] = ', '.join(cc_recipients)
    msg['Subject'] = email_subject

    # Attach the HTML content
    msg.attach(MIMEText(html_content, 'html'))

    # Set up the SMTP server
    smtp_host = 'smtp.office365.com'
    smtp_port = 587

    # Finally send message
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, email_recipients, msg.as_string())

    print(f"INFO  - Email sent successfully to recipients {email_recipients}.")


if __name__ == "__main__":

    current_datetime = datetime.now()
    days_ago = current_datetime - timedelta(days=365)
    start_publish_date = days_ago

    report_payload = build_report_payload(start_publish_date=days_ago)

    # # Load JSON data
    # with open(f"{files_path}/report_payload.json", "r", encoding="utf-8") as json_file:
    #     report_payload = json.load(json_file)
    # print("DEBUG - Loaded JSON data ", type(report_payload))

    # email_recipients = ["steven@icomm-net.com"]
    email_recipients = ["machado000@gmail.com"]
    cc_recipients = ["nivaldo@icomm-net.com"]

    send_email_report(report_payload, email_recipients, cc_recipients)
