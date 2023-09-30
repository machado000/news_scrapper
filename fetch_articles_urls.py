'''
news_scrapper
v.2023-09-23
'''

import hashlib
import json  # noqa
import os
from urllib.parse import urlparse

import feedparser
from dotenv import load_dotenv
from requests.exceptions import RequestException

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

    try:
        # Make the API request
        response = session.get(endpoint, params=params, headers=headers)
        response.raise_for_status()

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

    except RequestException as e:
        print(f"ERROR - An error occurred during the API request: {e}")
        return None, []


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

    # Initialize lists to store data
    all_entries = []
    all_links = []

    try:
        for rss_feed_url in rss_feed_urls:
            # Parse the RSS feed
            feed = feedparser.parse(rss_feed_url)

            if feed.get("entries"):
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

        print(f"INFO  - Found {len(all_links)} URLs in the given RSS feeds")

        return result_dict, all_links  # Return both the JSON and the list of entry.link values

    except Exception as e:
        print(f"ERROR - An error occurred while processing RSS feeds: {e}")
        return None, []


if __name__ == "__main__":

    # 1. FETCH URLS FROM BING API, UPDATE MONGODB
    try:
        mongo_cnx = MongoCnx("news_db")

        # Query keywords search list, loop `request_bing_news_urls()`
        collection = mongo_cnx.db["keywords"]
        keywords = collection.distinct("keyword", {"active": True})
        # print("DEBUG - ", keywords)

        handler = CustomRequests(username=proxy_username, password=proxy_password,
                                 endpoint=proxy_server, port=proxy_port)
        session = handler.session
        all_results_dict = {'news': []}

        for keyword in keywords:
            response_dict, _ = request_bing_news_urls(session, keyword, results_count=100, freshness="month")
            all_results_dict['news'].extend(response_dict['news'])

        result_json = json.dumps(all_results_dict, ensure_ascii=False, indent=4)
        with open('./files/bing_last_results.json', 'w', encoding='utf-8') as file:
            file.write(result_json)

        # Query active 'domains' on mongodb 'news_db.selectors', filter delete articles if not in list
        collection = mongo_cnx.db["selectors"]
        allowed_domains = collection.distinct("domain", {"active": True})
        print("DEBUG - allowed_domains: ", allowed_domains)

        all_results_dict['news'] = [item for item in all_results_dict['news'] if item['domain'] in allowed_domains]

        # Upsert final list on mongodb 'news_db.news'
        mongo_cnx.update_collection("news", all_results_dict["news"])

    except Exception as e:
        print("ERROR - ", e)

    # 2. FETCH URLS FROM WSJ RSS FEEDS, UPDATE MONGODB
    try:
        mongo_cnx = MongoCnx("news_db")

        # List RSS feeds, loop `extract_rss_article_urls()`
        rss_feed_urls = [
            "https://feeds.a.dj.com/rss/RSSOpinion.xml",
            "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
            "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            "https://feeds.a.dj.com/rss/RSSWSJD.xml",
            "https://feeds.a.dj.com/rss/RSSLifestyle.xml",
        ]

        response_dict, all_links = extract_rss_article_urls(rss_feed_urls)

        result_json = json.dumps(response_dict, ensure_ascii=False, indent=4)
        with open('./files/wsj_last_results.json', 'w', encoding='utf-8') as file:
            file.write(result_json)

        # Since all come from WSJ do not filter delete
        # Upsert final list on mongodb 'news_db.news'
        mongo_cnx.update_collection("news", response_dict["news"])

    except Exception as e:
        print("ERROR - ", e)
