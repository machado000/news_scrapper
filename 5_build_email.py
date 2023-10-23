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
from rapidfuzz import fuzz  # noqa

from src._drv_mongodb import MongoCnx

# Load variables from .env
load_dotenv()
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT')
# print("DEBUG - ", smtp_username, smtp_password, smtp_server, smtp_port) # noqa

html_files_path, json_files_path = "./html_files", "./json_files"
[os.makedirs(path) for path in [html_files_path, json_files_path] if not os.path.exists(path)]


# def match_keywords(source_collection, keyword_collection, destination_collection):
#     # Filter articles with keywords
#     print(f"\nINFO  - Filtering {source_collection.name} for keywords.")

#     # Keywords search list
#     query = keyword_collection.find({"active": True}, {"keyword": 1, "match_threshold": 1}).sort("keyword", 1)
#     keyword_list = list(query)
#     print("\n".join([f"DEBUG - keyword: {item['keyword']}" for item in keyword_list]))

#     filtered_list = []

#     for document in source_collection.find():
#         title = document.get("title", "").lower()  # Convert title to lowercase

#         for item in keyword_list:
#             keyword = item["keyword"].lower()
#             threshold = item.get("match_threshold", 80)
#             ratio = fuzz.partial_ratio(keyword, title)
#             # print("DEBUG - ", keyword, threshold, title)

#             if ratio >= threshold:
#                 document['keyword'] = keyword  # Add the matching keyword to document
#                 filtered_list.append(document)
#                 print(f"INFO  - '{keyword}' match with ~{ratio:.0f} on '{title[0:100]}'")
#                 break  # Exit the loop once a match is found

#     print(f"INFO  - Found {len(filtered_list)} matches.")

#     if filtered_list:
#         mongo_cnx.update_collection(destination_collection.name, filtered_list)

#     return None


def build_report_payload(collection_name=None, domain=None, min_score=None, start_publish_date=None, status=None):
    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")

    if collection_name is None:
        collection_name = "news"

    # 1. List keywords to be matched
    collection = mongo_cnx.db["keywords"]
    keyword_list = collection.distinct("keyword", {"active": True})
    keyword_list = [item.strip('"') for item in keyword_list]
    print("DEBUG - ", keyword_list)

    # 2. Match and update document statuses
    # matches = mongo_cnx.match_doc_with_keywords(
    #     collection_name, start_publish_date=start_publish_date, status=status, keyword_list=keyword_list)
    # print("DEBUG - ", matches)

    # mongo_cnx.update_collection("news", matches)

    # 3. Fetch documents with match to create email payload
    payload = mongo_cnx.get_doc_summary(collection_name=collection_name, domain=domain,
                                        min_score=min_score, start_publish_date=start_publish_date, status=status)

    if len(payload) > 0:
        print("INFO  - Last document _id:", payload[-1]["_id"], ", publish_date:", payload[-1]["publish_date"])

        for item in payload:
            if "publish_date" in item and isinstance(item["publish_date"], datetime):
                # Convert the datetime object to a string with the desired format
                item["publish_date"] = item["publish_date"].strftime("%m/%d/%Y")

            item["domain"] = item["domain"].replace("www.", "")

        with open(f"{json_files_path}/report_payload.json", "w", encoding="utf-8") as json_file:
            json.dump(payload, json_file)
        print(f"INFO  - Payload saved on \'{json_files_path}/report_payload.json\'.")

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
    days_ago = current_datetime - timedelta(days=3)
    start_publish_date = days_ago

    # match_keywords()

    report_payload = build_report_payload(collection_name="news", domain=None,
                                          min_score=7, start_publish_date=days_ago, status="ready")

    # Load JSON data
    with open(f"{json_files_path}/report_payload.json", "r", encoding="utf-8") as json_file:
        report_payload = json.load(json_file)
    print("DEBUG - Loaded JSON data ", type(report_payload))

    # email_recipients = ["steven@icomm-net.com"]
    email_recipients = ["machado000@gmail.com"]
    cc_recipients = ["nivaldo@icomm-net.com"]

    send_email_report(report_payload, email_recipients, cc_recipients)
