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

from src._decorators import retry
from src._drv_mongodb import MongoCnx

# Load variables from .env
load_dotenv()
openai_apikey = os.getenv('OPENAI_APIKEY')
# print("DEBUG - ", proxy_username, proxy_password, proxy_server, proxy_port, wsj_username, wsj_password, bing_apikey, openai_apikey) # noqa

html_files_path, json_files_path = "./html_files", "./json_files"
[os.makedirs(path) for path in [html_files_path, json_files_path] if not os.path.exists(path)]


def clean_text(text_str):
    text_str = re.sub(r'\n', ' ', text_str)
    text_str = ' '.join(text_str.split())

    valid_chars = set(string.printable)
    cleaned_text = ''.join(char for char in text_str if char in valid_chars)

    return cleaned_text


@retry()
def openai_summarize_text(input_text):
    try:
        print("INFO  - Querying OpenAI for article text summary.")

        openai.api_key = os.getenv('OPENAI_APIKEY')

        system_prompt = "Use a style suitable for business reports. Direct text to investors and business analysts. Write a single text block with no linkebreaks."  # noqa
        user_prompt_1 = f"Compose a 200-word summary of the following news article text: '{input_text}'"  # noqa

        response_1 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": user_prompt_1}
            ],
            temperature=0.5,
            max_tokens=300,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        # print("DEBUG - ", response_1)
        summary = response_1['choices'][0]['message']['content']

        # # Make a second API request
        # user_prompt_2 = "Now generate keywords related to the subject of this same news article."

        # response_2 = openai.ChatCompletion.create(
        #     model="gpt-3.5-turbo",
        #     messages=[
        # {"role": "assistant", "content": summary}
        #         {"role": "user", "content": user_prompt_2}
        #     ],
        #     temperature=0.5,
        #     max_tokens=150,
        #     top_p=1,
        #     frequency_penalty=0,
        #     presence_penalty=0
        # )
        # print("DEBUG - ", response_2)
        # keywords = response_2['choices'][0]['message']['content']

        if summary:
            print(f"INFO  - Response: '{summary[:120]}...'")

        return summary

    except Exception as e:
        print("ERROR - ", e)
        raise Exception


if __name__ == "__main__":

    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")
    file_path = f"{json_files_path}/articles_summaries.json"

    # 1. list articles to be summarized
    collection_name = "news_unprocessed"
    domain = None
    start_date = None  # datetime(2023, 10, 1, 12, 00)
    status = "content_parsed"

    articles = mongo_cnx.get_doc_content(collection_name=collection_name, domain=domain,
                                         start_publish_date=start_date, status=status)

    if articles == []:
        print("INFO  - Exiting program. No documents where found.")
        sys.exit()

    print("INFO  - Last document _id:", articles[-1]["_id"], ", publish_date:", articles[-1]["publish_date"])

    # 3-B. Generate article summary with OpenAI
    articles_summaries = []
    total_count = len(articles)

    for idx, item in enumerate(articles, start=1):
        try:
            # Send article text to openai and fetch summary
            article_body_text = item['content']
            cleaned_text = clean_text(article_body_text)

            summary = openai_summarize_text(cleaned_text)

            summary_entry = {
                "_id": item['_id'],
                "summary": summary,
                "status": "summarized",
            }

            articles_summaries.append(summary_entry)
            print(f"INFO  - {idx}/{total_count}   - article {item['_id']} summarized.")

        except Exception as e:
            print(f"ERROR - {idx}/{total_count} - Error fetching summary for document {item['_id']}: {str(e)}")
            continue  # Continue to the next item in case of an error

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(articles_summaries, json_file)

    # 4. Update Mongodb with new article summaries
    with open(file_path, "r", encoding="utf-8") as json_file:
        articles_contents = json.load(json_file)

    mongo_cnx = MongoCnx("news_db")
    mongo_cnx.update_collection(collection_name, articles_summaries)
