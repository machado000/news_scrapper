'''
news_scrapper
v.2023-10-02
'''
import json
import os
import re
import string
import sys
from datetime import datetime  # noqa

import openai
from dotenv import load_dotenv

from src._drv_mongodb import MongoCnx


# Load variables from .env
load_dotenv()
openai_apikey = os.getenv("OPENAI_APIKEY")
# print("DEBUG - ", proxy_username, proxy_password, proxy_server, proxy_port, wsj_username, wsj_password, bing_apikey, openai_apikey) # noqa

html_files_path, json_files_path = "./html_files", "./json_files"
[os.makedirs(path) for path in [html_files_path, json_files_path] if not os.path.exists(path)]


def clean_text(text_str):
    text_str = re.sub(r'\n', ' ', text_str)
    text_str = " ".join(text_str.split())

    valid_chars = set(string.printable)
    cleaned_text = "".join(char for char in text_str if char in valid_chars)

    return cleaned_text


def openai_summarize_text(input_text):
    try:
        print("INFO  - Querying OpenAI for article text summary.")

        openai.api_key = os.getenv("OPENAI_APIKEY")

        system_prompt = "Use a style suitable for business reports with text directed to investors and \
            business analysts. Write a single text block with no linebreaks."  # noqa

        user_prompt_1 = f'Summarize the text delimited by triple quotes in about 200 words: \"\"\"{input_text}\"\"\"'  # noqa

        response_1 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": user_prompt_1}
            ],
            temperature=0.5,
            max_tokens=320,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        # print("DEBUG - ", response_1)
        summary = response_1["choices"][0]["message"]["content"]

        if summary:
            print(f"INFO  - Response: `{summary[:120]}...`")

        return summary

    except Exception as e:
        print("ERROR - ", e)
        raise Exception


if __name__ == "__main__":

    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")
    file_path = f"{json_files_path}/articles_summaries.json"

    # 1. list articles to be summarized
    collection_name = "news"  # or news_unprocessed
    domain = None
    start_date = None  # datetime(2023, 10, 1, 12, 00)
    status = "content_parsed"  # or "invalid_summary" to retry errors

    articles_list = mongo_cnx.get_doc_content(collection_name=collection_name, domain=domain,
                                              min_score=7, start_publish_date=start_date, status=status)

    if articles_list == []:
        print("INFO  - Exiting program. No documents where found.")
        sys.exit(1)

    print("INFO  - Last document _id:", articles_list[-1]["_id"], ", publish_date:", articles_list[-1]["publish_date"])

    # 3. Generate article summary with OpenAI
    result_list = []
    total_count = len(articles_list)

    for idx, item in enumerate(articles_list, start=1):
        print(f'\nINFO  - {idx}/{total_count}  - fetching article `{item["title"][0:200]}`, document {item["_id"]}.')
        try:
            # Send article text to openai and fetch summary
            article_body_text = item["content"]
            cleaned_text = clean_text(article_body_text)
            # print(cleaned_text)  # DEBUG

            summary = openai_summarize_text(cleaned_text)

            document_entry = {
                "_id": item["_id"],
                "summary": summary,
                "status": "summarized",
            }
            result_list.append(document_entry)

        except Exception as e:
            document_entry = {
                "_id": item["_id"],
                "summary": None,
                "status": "invalid_summary",
            }
            result_list.append(document_entry)
            print(f'ERROR - {idx}/{total_count} - Failure fetching summary for document {item["_id"]}:', e)
            continue  # Continue to the next item in case of an error

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(result_list, json_file)

    # 4. Update Mongodb with new article summaries
    with open(file_path, "r", encoding="utf-8") as json_file:
        result_list = json.load(json_file)

    mongo_cnx = MongoCnx("news_db")
    mongo_cnx.update_collection(collection_name, result_list)
