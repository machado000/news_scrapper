#!/home/master/apps/13dnews/venv/bin/python3
'''
news_scrapper
v.2023-10-02
'''

import hashlib
import json  # noqa
import os
from dateutil import parser
from urllib.parse import urlparse

import feedparser
from dotenv import load_dotenv
from rapidfuzz import fuzz
from requests.exceptions import RequestException

from src._decorators import retry
from src._drv_mongodb import MongoCnx
from src._drv_scrapers import CustomRequests

# Load variables from .env
load_dotenv()
proxy_username = os.getenv("PROXY_USERNAME")
proxy_password = os.getenv("PROXY_PASSWORD")
proxy_server = os.getenv("PROXY_SERVER")
proxy_port = os.getenv("PROXY_PORT")
wsj_username = os.getenv("WSJ_USERNAME")
wsj_password = os.getenv("WSJ_PASSWORD")
bing_apikey = os.getenv("BING_APIKEY")
# print(proxy_username, proxy_password, proxy_server, proxy_port, wsj_username, wsj_password, bing_apikey, openai_apikey)  # noqa

files_path = "./news_data"
if not os.path.exists(files_path):
    os.makedirs(files_path)


def convert_date_string_to_iso(date_str):
    """
    Convert a date string to an ISO-8601 formatted date string.

    Args:
        date_str (str): The date string in a recognized format.

    Returns:
        str: An ISO-8601 formatted date string.

    Supported date formats:
        'Wed, 04 Oct 2023 20:00:00 GMT' and 'Wed, 04 Oct 2023 20:00:00 -0400'
    """
    try:
        date_obj = parser.parse(date_str)
        iso_date_str = date_obj.isoformat()

    except ValueError as e:
        raise ValueError(f"Invalid date format: {str(e)}.")

    return iso_date_str


def filter_news_dict(news_obj_list, keyword_list):
    # Filter articles with keywords
    print(f"\nINFO  - Filtering {len(news_obj_list)} items for keywords.")
    filtered_list = []

    for news_item in news_obj_list:
        title = news_item.get("title", "").lower()  # Convert title to lowercase

        for item in keyword_list:
            keyword = item["keyword"].lower()
            threshold = item.get("match_threshold", 80)
            # print("DEBUG - ", keyword, threshold, title)

            if fuzz.partial_ratio(keyword, title) >= threshold:
                news_item['keyword'] = keyword  # Add the matching keyword to news_item
                filtered_list.append(news_item)
                print(f"INFO  - Keyword '{keyword}' match on '{title[0:100]}'")
                break  # Exit the loop once a match is found

    print(f"INFO  - Found {len(filtered_list)} matches.")

    return filtered_list


@retry()
def request_bing_news_urls(session, query, results_count=100, freshness="day"):
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
    headers = {"Ocp-Apim-Subscription-Key": bing_apikey}
    print(f"\nINFO  - Querying {endpoint} for {query}")

    try:
        # Make the API request
        response = session.get(endpoint, params=params, headers=headers)
        response.raise_for_status()

        response_data = response.json()

        # Build JSON with results data
        all_entries = []

        for entry in response_data['value']:
            url = entry.get("url", "")
            url_hash = hashlib.md5(url.encode()).hexdigest()
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")

            extracted_entry = {
                "_id": url_hash,
                # "source": "Bing",
                "category": entry.get("category", ""),
                "domain": domain,
                "publish_date": entry.get("datePublished", ""),
                "title": entry.get("name", ""),
                "url": url,
                "status": "fetched",
            }

            all_entries.append(extracted_entry)

        results = all_entries
        print(f"INFO  - Found {len(results)} entries with query '{query}'.")

        return results

    except RequestException as e:
        print(f"ERROR - An error occurred during the API request: {e}")
        return None


@retry()
def extract_rss_article_urls(handler, rss_url):
    """
    Extracts article data from an RSS feed URL.

    Args:
        handler: The session handler for making HTTP requests.
        rss_url (str): The URL of the RSS feed.

    Returns:
        dict: JSON-compatible dict containing extracted article data.
    """

    try:
        # Use the session object to fetch the RSS feed
        print(f"\nINFO  - Fetching articles on RSS Feed '{rss_url}'")
        response = handler.get_response(rss_url)
        response.raise_for_status()

        feed_content = response.text
        feed = feedparser.parse(feed_content)

        # Build JSON with results data
        all_entries = []

        for entry in feed.entries:
            # Extract MD5 hash (_id) and domain from article url
            url = entry.get("link", "")
            url_hash = hashlib.md5(url.encode()).hexdigest()
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")

            # Convert date from "Sat, 30 Sep 2023 02:33:34 -0400" inti ISO format
            pubDdate = entry.get("published", "")
            published_date = convert_date_string_to_iso(pubDdate)

            # Extract article data
            extracted_entry = {
                "_id": url_hash,
                "domain": domain,
                "publish_date": published_date,
                "title": entry.get("title", ""),
                "url": url,
                "status": "fetched",
            }
            all_entries.append(extracted_entry)

        results = all_entries
        print(f"INFO  - Found {len(results)} entries.")

        return results

    except Exception as e:
        print(f"ERROR - An error occurred while processing RSS feeds: {e}")
        return {}


if __name__ == "__main__":
    # =============== 0. INITIAL CONFIG ===============
    handler = CustomRequests(username=proxy_username, password=proxy_password,
                             endpoint=proxy_server, port=proxy_port)
    session = handler.session

    mongo_cnx = MongoCnx("news_db")

    # Query keywords search list
    collection = mongo_cnx.db['keywords']
    query = collection.find({"active": True}, {"keyword": 1, "match_threshold": 1})
    keyword_list = list(query)
    # print(list(keyword_list))

    # =============== 1. FETCH URLS FROM BING API, UPDATE MONGODB ===============
    collection = mongo_cnx.db['sources']
    allowed_domains = collection.distinct("domain", {"active": True})
    # print("DEBUG - allowed_domains:", allowed_domains)

    all_results = []

    for item in keyword_list:
        keyword = item["keyword"]
        result = request_bing_news_urls(session=session, query=f'"{keyword}"', freshness="month")
        all_results.extend(result)

    # Filter allowed domains
    domain_results = [item for item in all_results if item['domain'] in allowed_domains]
    print(f"\nINFO  - Found {len(domain_results)} entries with valid domains")
    # Filter titles for keywords
    filtered_results = filter_news_dict(domain_results, keyword_list)
    news_obj_list = domain_results

    # Save local JSON
    filtered_results_json = json.dumps(filtered_results, ensure_ascii=False, indent=4)

    with open(f"./{files_path}/bing_last_results.json", "w", encoding="utf-8") as file:
        file.write(filtered_results_json)
    print(f"\nINFO  - Saved {len(filtered_results)} results on '{files_path}/bing_last_results.json'")

    # Upsert final list on mongodb "news_db.news"
    mongo_cnx.insert_documents("news", filtered_results)

    # =============== 2. FETCH URLS FROM RSS FEEDS, UPDATE MONGODB ===============
    collection = mongo_cnx.db['sources']
    rss_url_list = collection.distinct("rss_list", {"active": True})
    # print("DEBUG - ", rss_url_list)

    all_results = []

    for rss_url in rss_url_list:
        result = extract_rss_article_urls(handler, rss_url)
        all_results.extend(result)

    # Filter titles for keywords
    filtered_results = filter_news_dict(all_results, keyword_list)

    # Save local JSON
    filtered_results_json = json.dumps(filtered_results, ensure_ascii=False, indent=4)

    with open(f"{files_path}/rss_last_results.json", "w", encoding="utf-8") as file:
        file.write(filtered_results_json)
    print(f"\nINFO  - Saved {len(filtered_results)} results on '{files_path}/rss_last_results.json'")

    # Insert matches on mongodb "news_db.news"
    mongo_cnx.insert_documents("news", filtered_results)
