'''
news_scrapper
v.2023-09-23
'''

import hashlib
import json  # noqa
import os

import feedparser
from urllib.parse import urlparse
from dotenv import load_dotenv

from src._drv_mongodb import MongoCnx
from src._drv_scrapers import CustomRequests

# Load variables from .env
load_dotenv()
proxy_username = os.getenv('PROXY_USERNAME')
proxy_password = os.getenv('PROXY_PASSWORD')
proxy_server = os.getenv('PROXY_SERVER')
proxy_port = os.getenv('PROXY_PORT')
wsj_username = os.getenv('WSJ_USERNAME')
wsj_password = os.getenv('WSJ_PASSWORD')
bing_apikey = os.getenv('BING_APIKEY')
# print(proxy_username, proxy_password, proxy_server, proxy_port, wsj_username, wsj_password, bing_apikey, openai_apikey)  # noqa

files_path = "./files"

if not os.path.exists(files_path):
    os.makedirs(files_path)


def request_bing_news_urls(session, query, category=None, results_count=100, freshness="day"):
    """
    Query Bing News API for news article urls.

    Args:
    - session (requests object) for connection option like proxy
    - query (str) using Bing News API operators

    Returns:
    - tuple: A tuple containing:
        - dict: JSON-compatible dict containing extracted article data.
        - list: List of all 'entry.link' values.
    """
    endpoint = "https://api.bing.microsoft.com/v7.0/news/search"

    params = {
        "q": query,
        # "category": category,
        "count": results_count,
        "freshness": freshness,
        "mkt": "en-US",
        "setLang": "en"
    }

    print(f"\nINFO  - Querying {endpoint} for {query}")

    headers = {
        "Ocp-Apim-Subscription-Key": bing_apikey
    }

    # Make the API request
    response = session.get(endpoint, params=params, headers=headers)

    if response.status_code == 200:
        response_data = response.json()

        results = []
        all_links = []

        for value in response_data["value"]:
            url = value.get("url", "")
            url_hash = hashlib.md5(url.encode()).hexdigest()
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            extracted_entry = {
                "_id": url_hash,
                "url": url,
                "title": value.get("name", ""),
                "summary": value.get("description", ""),
                "publish_date": value.get("datePublished", ""),
                "source": "Bing",
                "domain": domain,
            }
            results.append(extracted_entry)

            all_links.append(value.get("url", ""))

        # Create a dictionary for the extracted data
        result_dict = {"news": results}

        print(f"INFO  - Found {len(all_links)} urls with given parameters")

        return result_dict, all_links  # Return both the JSON and the list of entry.link values


def extract_rss_article_urls(rss_feed_urls):
    """
    Extracts article data from a list of RSS feed URLs.

    Args:
    - rss_feed_urls (list): List of RSS feed URLs.

    Returns:
    - tuple: A tuple containing:
        - dict: JSON-compatible dict containing extracted article data.
        - list: List of all 'entry.link' values.
    """
    print(f"\nINFO  - Quering {len(rss_feed_urls)} RSS feeds for article urls")

    # Loop through the list of feed URLs
    all_entries = []
    all_links = []  # Initialize a list to store entry.link values

    for rss_feed_url in rss_feed_urls:
        # Parse the RSS feed
        feed = feedparser.parse(rss_feed_url)

        # Append the feed data to the list
        all_entries.extend(feed.entries)

        # Extract and append entry.link values to the list
        all_links.extend([entry.get("link", "") for entry in feed.entries])

    extracted_data = []

    for entry in all_entries:
        url = entry.get("link", "")
        url_hash = hashlib.md5(url.encode()).hexdigest()
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        extracted_entry = {
            "_id": url_hash,
            "url": url,
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "publish_date": entry.get("published", ""),
            "source": "WSJ",
            "domain": domain,
        }
        extracted_data.append(extracted_entry)

    # Create a dictionary for the extracted data
    result_dict = {"news": extracted_data}

    print(f"INFO  - Found {len(all_links)} urls on given RSS feeds")

    return result_dict, all_links  # Return both the JSON and the list of entry.link values


if __name__ == "__main__":

    # FETCH URLS FROM BING API, UPDATE MONGODB
    mongo_cnx = MongoCnx("news_db")
    collection = mongo_cnx.db["keywords"]

    query_result = collection.find({"active": True})
    keywords = [document["keyword"] for document in query_result]
    print("DEBUG - ", keywords)

    handler = CustomRequests(username=proxy_username, password=proxy_password, endpoint=proxy_server, port=proxy_port)
    session = handler.session

    for keyword in keywords:
        response_dict, _ = request_bing_news_urls(session, keyword, results_count=100, freshness="month")
        mongo_cnx.update_collection("news", response_dict["news"])

        # result_json = json.dumps(response_dict, ensure_ascii=False, indent=4)
        # with open('./files/bing_last_results.json', 'w', encoding='utf-8') as file:
        #     file.write(result_json)

    # FETCH URLS FROM WSJ RSS FEEDS, UPDATE MONGODB
    rss_feed_urls = [
        "https://feeds.a.dj.com/rss/RSSOpinion.xml",
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://feeds.a.dj.com/rss/RSSWSJD.xml",
        "https://feeds.a.dj.com/rss/RSSLifestyle.xml",
    ]

    response_dict, all_links = extract_rss_article_urls(rss_feed_urls)

    mongo_cnx = MongoCnx("news_db")
    mongo_cnx.update_collection("news", response_dict["news"])

    # result_json = json.dumps(response_dict, ensure_ascii=False, indent=4)
    # with open('./files/wsj_last_results.json', 'w', encoding='utf-8') as file:
    #     file.write(result_json)
