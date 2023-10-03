'''
news_scrapper
v.2023-10-02
'''
import json
import sys
import os
from datetime import datetime  # noqa

import openai
from dotenv import load_dotenv

from src._drv_mongodb import MongoCnx
from src._decorators import retry

# Load variables from .env
load_dotenv()
openai_apikey = os.getenv('OPENAI_APIKEY')
# print("DEBUG - ", proxy_username, proxy_password, proxy_server, proxy_port, wsj_username, wsj_password, bing_apikey, openai_apikey) # noqa


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
            print(f"INFO  - Response: '{summary[:100]}...'")

        return summary

    except Exception as e:
        print("ERROR - ", e)
        raise Exception


if __name__ == "__main__":

    # 0. Initial settings
    files_path = "./news_data"
    if not os.path.exists(files_path):
        os.makedirs(files_path)

    mongo_cnx = MongoCnx("news_db")

    # 1. list articles to be scraped
    collection_name = "news"
    domain = None
    start_date = None  # datetime(2023, 10, 1, 12, 00)
    status = "content_parsed"
    articles = mongo_cnx.get_doc_content(collection_name=collection_name, domain=domain,
                                         start_publish_date=start_date, status=status)

    if articles == []:
        print("INFO  - Exiting program. No documents where found.")
        sys.exit()

    print("INFO  - Last document _id:", articles[-1]["_id"], ", publish_date:", articles[-1]["publish_date"])

    # 3-B. Fetch and save page HTML soup and article_body.text, generate article summary with OpenAI
    articles_summaries = []
    total_count = len(articles)

    for idx, item in enumerate(articles, start=1):
        try:
            # Send article text to openai and fetch summary
            article_body_text = item['content']
            summary = openai_summarize_text(article_body_text)

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

    with open(f"{files_path}/articles_summaries.json", "w", encoding="utf-8") as json_file:
        json.dump(articles_summaries, json_file)

    # 4. Update Mongodb with new article summaries
    with open(f"{files_path}/articles_summaries.json", "r", encoding="utf-8") as json_file:
        articles_contents = json.load(json_file)

    mongo_cnx = MongoCnx("news_db")
    mongo_cnx.update_collection("news", articles_summaries)
