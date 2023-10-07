#!/home/master/apps/13dnews/venv/bin/python3
'''
news_scrapper
v.2023-10-02
'''

import hashlib
import json  # noqa
import os
from urllib.parse import urlencode, urlparse

import feedparser
from datetime import datetime, timedelta
from dateutil import parser
from dotenv import load_dotenv
from rapidfuzz import fuzz
from requests.exceptions import HTTPError, RequestException

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

html_files_path, json_files_path = "./html_files", "./json_files"
[os.makedirs(path) for path in [html_files_path, json_files_path] if not os.path.exists(path)]


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


def generate_google_news_rss_query(keyword, days_ago=None, language="en-US", location="US", edition="US:en", num_results=100):  # noqa
    base_url = "https://news.google.com/rss/search?"

    # Prepare the query parameters
    params = {
        "q": keyword,
        "hl": language,
        "gl": location,
        "ceid": edition,
        "num": num_results,
    }

    # Add date range if specified
    if days_ago is not None:
        min_date = f"cd_min:{days_ago},"
        params["tbs"] = f"cdr:1,{min_date}cd_max:today"

    # Sort by relevance '1' or date '0'
    params["so"] = 1

    # Construct the URL
    query_string = urlencode(params)
    full_url = f"{base_url}{query_string}"

    return full_url


def extract_commom_news_rss(handler, rss_url):
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
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")
            clean_url = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
            url_hash = hashlib.md5(clean_url.encode()).hexdigest()

            # Convert date from "Sat, 30 Sep 2023 02:33:34 -0400" inti ISO format
            pubDdate = entry.get("published", "")
            published_date = convert_date_string_to_iso(pubDdate)

            # Extract article data
            extracted_entry = {
                "_id": url_hash,
                "source": "RSS feed",
                "domain": domain,
                "publish_date": published_date,
                "title": entry.get("title", ""),
                # "rss_summary": entry.get("summary", ""),
                "url": clean_url,
                "status": "fetched",
            }
            all_entries.append(extracted_entry)

        results = all_entries
        print(f"INFO  - Found {len(results)} entries.")

        return results

    except Exception as e:
        print(f"ERROR - An error occurred while processing RSS feeds: {e}")
        return {}


def extract_google_news_rss(handler, rss_url):
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
        print(f"\nINFO  - Fetching entries on feed '{rss_url[0:100]}'")
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
            source_url = entry.source.get("url", "")
            parsed_url = urlparse(source_url)
            domain = parsed_url.netloc.replace("www.", "")

            # Convert date from "Sat, 30 Sep 2023 02:33:34 -0400" inti ISO format
            pubDdate = entry.get("published", "")
            published_date = convert_date_string_to_iso(pubDdate)

            # Extract article data
            extracted_entry = {
                "_id": url_hash,
                "source": "Google News",
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


def filter_news_titles(news_obj_list, keyword_list):
    # Filter articles with keywords
    print(f"\nINFO  - Filtering {len(news_obj_list)} items for keywords.")
    filtered_list = []

    for news_item in news_obj_list:
        title = news_item.get("title", "").lower()  # Convert title to lowercase

        for item in keyword_list:
            keyword = item["keyword"].lower()
            threshold = item.get("match_threshold", 80)
            ratio = fuzz.partial_ratio(keyword, title)
            # print("DEBUG - ", keyword, threshold, title)

            if ratio >= threshold:
                news_item['keyword'] = keyword  # Add the matching keyword to news_item
                filtered_list.append(news_item)
                print(f"INFO  - '{keyword}' match with ~{ratio:.0f} on '{title[0:100]}'")
                break  # Exit the loop once a match is found

    print(f"INFO  - Found {len(filtered_list)} matches.")

    return filtered_list


def request_bing_news_urls(handler, query, results_count=100, freshness="day"):
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
        response = handler.get_response(endpoint, params=params, headers=headers)
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

    except HTTPError as e:
        if e.response.status_code == 403 or e.response.status_code == 429:
            print("INFO - 'Too Many Requests' error. Retrying...")
            raise  # This will trigger the retry mechanism
        else:
            print(f"INFO - Failed to get response: {e}")
            raise Exception(f"HTTP Error: {e}")

    except RequestException as e:
        print(f"ERROR - An error occurred during the API request: {e}")
        return None


if __name__ == "__main__":
    # =============== 0. INITIAL CONFIG ===============
    handler = CustomRequests(username=proxy_username, password=proxy_password,
                             endpoint=proxy_server, port=proxy_port)
    mongo_cnx = MongoCnx("news_db")

    # Keywords search list
    collection = mongo_cnx.db['keywords']
    query = collection.find({"active": True}, {"keyword": 1, "match_threshold": 1}).sort("keyword", 1)
    keyword_list = list(query)
    print("\n".join([f"DEBUG - keyword: {item['keyword']}" for item in keyword_list]))

    # Allowed domains list
    collection = mongo_cnx.db['sources']
    allowed_domains = collection.distinct("domain", {"active": True})
    print("\n".join([f"DEBUG - allowed_domains: {item}" for item in allowed_domains]))

    # =============== 2. FETCH URLS FROM RSS FEEDS, CLEAN, UPDATE MONGODB ===============

    collection = mongo_cnx.db['sources']
    commom_rss_url_list = collection.distinct("rss_list", {"active": True})

    # Fetch urls in commom news RSS
    commom_rss_results = []
    for rss_url in commom_rss_url_list:
        result = extract_commom_news_rss(handler, rss_url)
        commom_rss_results.extend(result)
    # print("\n".join([f"DEBUG - {item['url']}" for item in commom_rss_results]))
    print(f"DEBUG - Found {len(commom_rss_results)} results in commom RSS")

    # Build Google News RSS links
    google_rss_url_list = []
    for item in keyword_list:
        keyword = item["keyword"]
        rss_url = generate_google_news_rss_query(keyword=keyword, days_ago=2, num_results=100)
        google_rss_url_list.append(rss_url)
    # print("\n".join([f"DEBUG - {item}" for item in google_rss_url_list]))

    # Fetch urls in Goggle News Search RSS
    google_rss_results = []
    for rss_url in google_rss_url_list:
        result = extract_google_news_rss(handler, rss_url)
        google_rss_results.extend(result)
    # print("\n".join([f"DEBUG - {item['url']}" for item in google_rss_results]))
    print(f"DEBUG - Found {len(google_rss_results)} results in Google News")

    # Join results
    all_results = []
    # Copy for a different memory address
    first_list = [x for x in commom_rss_results] if 'commom_rss_results' in locals() else None
    second_list = [y for y in google_rss_results] if 'google_rss_results' in locals() else None

    all_results = first_list + second_list
    print(f"DEBUG - Found {len(all_results)} total results")

    # Filter out dates before
    date_results = []
    days_ago = 10
    date_obj = datetime.now() - timedelta(days=days_ago)
    iso_date_str = date_obj.isoformat()    # print(iso_date_str)
    date_results = [item for item in all_results[:] if item["publish_date"] >= iso_date_str]
    # print("\n".join([f"DEBUG - {item['url']}" for item in date_results]))
    print(f"\nINFO  - Found {len(date_results)} entries with valid publish dates")

    # Filter allowed domains
    domain_results = []
    domain_results = [item for item in date_results if item['domain'] in allowed_domains]
    # print("\n".join([f"DEBUG - {item['url'][0:120]}" for item in domain_results]))
    print(f"\nINFO  - Found {len(domain_results)} entries with valid domains")

    # Get redirected urls and update "_id" hash value
    valid_results = []

    for index, item in enumerate(domain_results, start=1):
        initial_url = item.get("url")
        parsed_url_temp = urlparse(initial_url)
        if parsed_url_temp.netloc == "news.google.com":
            final_url = handler.get_redirected_url(initial_url)
            parsed_url = urlparse(final_url)
            clean_url = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
            url_hash = hashlib.md5(clean_url.encode()).hexdigest()

            item["_id"] = url_hash
            item["url"] = clean_url
            print(f"INFO  - {index}/{len(domain_results)}  - redirect > {final_url[0:120]}")

        valid_results.append(item)

    # Save local JSON
    valid_results_json = json.dumps(valid_results, ensure_ascii=False, indent=4)

    mongo_cnx.insert_documents("news_unprocessed", valid_results)

    with open(f"{json_files_path}/valid_results_json.json", "w", encoding="utf-8") as file:
        file.write(valid_results_json)
    print(f"\nINFO  - Saved file on results on '{json_files_path}/valid_results_json")

    # with open(f"{json_files_path}/valid_results_json.json", "r", encoding="utf-8") as json_file:
    #     valid_results = json.load(json_file)

    # Filter titles for keywords
    filtered_results = []
    filtered_results = filter_news_titles(valid_results, keyword_list)
    print(f"\nINFO  - Found {len(filtered_results)} entries with valid titles")

    # Insert matches on mongodb "news_db.news"

    mongo_cnx.insert_documents("news", filtered_results)

    # =============== 1. FETCH URLS FROM BING API, UPDATE MONGODB ===============
    # collection = mongo_cnx.db['sources']
    # allowed_domains = collection.distinct("domain", {"active": True})
    # # print("DEBUG - allowed_domains:", allowed_domains)

    # all_results = []

    # for item in keyword_list:
    #     keyword = item["keyword"]
    #     result = request_bing_news_urls(handler=handler, query=f'"{keyword}"', freshness="day")
    #     all_results.extend(result)

    # # Filter allowed domains
    # domain_results = [item for item in all_results if item['domain'] in allowed_domains]
    # print(f"\nINFO  - Found {len(domain_results)} entries with valid domains")
    # # Filter titles for keywords
    # filtered_results = filter_news_dict(domain_results, keyword_list)
    # news_obj_list = domain_results

    # # Save local JSON
    # filtered_results_json = json.dumps(filtered_results, ensure_ascii=False, indent=4)

    # with open(f"./{json_files_path}/bing_last_results.json", "w", encoding="utf-8") as file:
    #     file.write(filtered_results_json)
    # print(f"\nINFO  - Saved {len(filtered_results)} results on '{json_files_path}/bing_last_results.json'")

    # # Upsert final list on mongodb "news_db.news"
    # mongo_cnx.insert_documents("news", filtered_results)
