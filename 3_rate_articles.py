'''
news_scrapper
v.2023-10-02
'''
import json
import os
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


def openai_score_text(input_text, keyword_list):
    try:
        print("INFO  - Querying OpenAI to rate article text with keywords.")

        openai.api_key = os.getenv("OPENAI_APIKEY")

        system_prompt = f'Consider the field of shareholder activism, which involves investors, often referred to \
            as activist shareholders, taking actions to influence or change the management and governance of \
            publicly traded companies. Consider the following keywords related to this field: {keyword_list}.'

        user_prompt_1 = f'In a scale from 0 to 10 score the relevance of the text delimited by triple quotes with \
            the field of shareholder activism. Return an integer and a short explanation for the rating, in format of \
            a JSON string with keys "score" and "explanation" . \"\"\"{input_text}\"\"\"'  # noqa

        response_1 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": user_prompt_1}
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
    collection_name = "news_unprocessed"
    domain = None
    start_date = None  # datetime(2023, 10, 1, 12, 00)
    status = "summarized"  # or "invalid_summary" to retry errors

    articles = mongo_cnx.get_doc_content(collection_name=collection_name, domain=domain,
                                         start_publish_date=start_date, status=status)

    if articles == []:
        print("INFO  - Exiting program. No documents where found.")
        sys.exit()

    print("INFO  - Last document _id:", articles[-1]["_id"], ", publish_date:", articles[-1]["publish_date"])

    # 2. Keywords search list
    keyword_collection = mongo_cnx.db["keywords"]
    query = keyword_collection.find({"active": True}, {"keyword": 1}).sort("keyword", 1)
    keyword_list = [document.get("keyword") for document in query]
    print("INFO  - Keyword list:", keyword_list)

    # 3. Rate article text with OpenAI
    document_list = []
    total_count = len(articles)

    for idx, item in enumerate(articles, start=1):
        print(f'\nINFO  - {idx}/{total_count}  - fetching document {item["_id"]}, `{item["title"][0:120]}`.')
        try:
            # Send article text to openai and fetch summary
            article_body_text = item["content"]
            response_dict = openai_score_text(article_body_text, keyword_list)

            document_entry = {
                "_id": item["_id"],
                "score": response_dict["score"],
                "explanation": response_dict["explanation"],
            }
            document_list.append(document_entry)

        except Exception as e:
            print(f'ERROR - {idx}/{total_count} - Failure fetching summary for document {item["_id"]}:', e)
            continue  # Continue to the next item in case of an error

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(document_list, json_file)

    # 4. Update Mongodb with new article summaries
    with open(file_path, "r", encoding="utf-8") as json_file:
        document_list = json.load(json_file)

    mongo_cnx = MongoCnx("news_db")
    mongo_cnx.update_collection(collection_name, document_list)
