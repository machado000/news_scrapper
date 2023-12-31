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


def openai_score_text(input_text, keyword_list):
    try:
        print("INFO  - Querying OpenAI to rate article text with keywords.")

        openai.api_key = os.getenv("OPENAI_APIKEY")

        system_prompt = f'You are an assistant to value correlation between texts to fields of business and finance.\
            I need you to score the relevance of text in the user prompt to the following keywords: {keyword_list}.\
            Return a score between 0 and 10 and a short explanation for the rating in format of a JSON string with \
            keys "score" and "explanation"'

        user_prompt_1 = f'\"\"\"{input_text}\"\"\"'  # noqa

        response_1 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_1}
            ],
            temperature=0.7,
            max_tokens=320,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        # print("DEBUG - ", response_1)
        content = response_1["choices"][0]["message"]["content"]
        response_dict = json.loads(content)

        if content:
            print(
                f'INFO  - Response: text scored {response_dict["score"]}/10 related to field `shareholder activism`')

        return response_dict

    except Exception as e:
        print("ERROR - ", e)
        raise Exception


if __name__ == "__main__":

    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")
    file_path = f"{json_files_path}/articles_scores.json"

    # 1. list articles to be scored
    collection = mongo_cnx.db["news"]

    query = {
        'score': {'$exists': False},  # Check for the absence of 'score'
        'content': {'$exists': True}   # Check for the presence of 'content'
    }
    projection = {"_id": 1, "publish_date": 1, "title": 1, "content": 1}

    cursor = collection.find(query, projection=projection)
    articles_list = [document for document in cursor]
    # print("INFO  - Document list:", articles_list)

    if articles_list == []:
        print("INFO  - Exiting program. No documents where found.")
        sys.exit(1)

    print("INFO  - Last document _id:", articles_list[-1]["_id"], ", publish_date:", articles_list[-1]["publish_date"])

    # 2. Keywords search list
    keyword_collection = mongo_cnx.db["keywords"]
    query = keyword_collection.find({"active": True}, {"keyword": 1}).sort("keyword", 1)
    keyword_list = [document.get("keyword") for document in query]
    print("INFO  - Keyword list:", keyword_list)

    # 3. Rate article text with OpenAI
    result_list = []
    total_count = len(articles_list)

    for idx, item in enumerate(articles_list, start=1):
        print(f'\nINFO  - {idx}/{total_count}  - fetching document {item["_id"]}, `{item["title"][0:120]}`.')
        try:
            # Send article text to openai and fetch summary
            article_body_text = item["content"]
            cleaned_text = clean_text(article_body_text)
            response_dict = openai_score_text(cleaned_text, keyword_list)

            document_entry = {
                "_id": item["_id"],
                "score": response_dict["score"],
                "explanation": response_dict["explanation"],
            }
            result_list.append(document_entry)

        except Exception as e:
            print(f'ERROR - {idx}/{total_count} - Failure fetching summary for document {item["_id"]}:', e)
            continue  # Continue to the next item in case of an error

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(result_list, json_file)

    # 4. Update Mongodb with new article summaries
    with open(file_path, "r", encoding="utf-8") as json_file:
        result_list = json.load(json_file)

    mongo_cnx = MongoCnx("news_db")
    mongo_cnx.update_collection("news", result_list)
