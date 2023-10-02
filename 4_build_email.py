'''
news_scrapper
v.2023-09-23
'''
import json
import os

from datetime import datetime
from dotenv import load_dotenv

from src._drv_mongodb import MongoCnx

# Load variables from .env
load_dotenv()
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT')
# print("DEBUG - ", smtp_username, smtp_password, smtp_server, smtp_port, wsj_username, wsj_password, bing_apikey, openai_apikey) # noqa


if __name__ == "__main__":

    # 0. Initial settings
    files_path = "./news_data"
    if not os.path.exists(files_path):
        os.makedirs(files_path)

    mongo_cnx = MongoCnx("news_db")

    collection_name = "news"
    start_publish_date = datetime(2023, 10, 1, 0, 0)
    status = "summarized"

    # 1. List keywords to be matched
    collection = mongo_cnx.db["keywords"]
    keyword_list = collection.distinct("keyword", {"active": True})
    keyword_list = [item.strip('"') for item in keyword_list]
    print("DEBUG - ", keyword_list)

    # 2. Match and update document statuses
    matches = mongo_cnx.match_doc_with_keywords(
        collection_name, start_publish_date=None, status="summarized", keyword_list=keyword_list)
    print(matches)

    mongo_cnx.update_collection("news", matches)

    # 3. Fetch documents with match to create email payload
    status = "matched"
    payload = mongo_cnx.get_doc_summary(collection_name=collection_name,
                                        start_publish_date=start_publish_date, status=status)

    if len(payload) > 0:
        print("INFO  - Last document _id:", payload[-1]["_id"], ", publish_date:", payload[-1]["publish_date"])

        for item in payload:
            if "publish_date" in item and isinstance(item["publish_date"], datetime):
                # Convert the datetime object to a string with the desired format
                item["publish_date"] = item["publish_date"].strftime("%m/%d/%Y")

            item["domain"] = item["domain"].replace("www.", "")

        with open(f"./{files_path}/email_payload.json", "w", encoding="utf-8") as json_file:
            json.dump(payload, json_file)
