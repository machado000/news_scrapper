'''
news_scrapper
v.2023-09-23
'''

import feedparser
import json
import pandas as pd

import src._drv_scrapers  # noqa


def extract_rss_article_data(rss_feed_urls):
    """
    Extracts article data from a list of RSS feed URLs.

    Args:
    - rss_feed_urls (list): List of RSS feed URLs.

    Returns:
    - tuple: A tuple containing:
        - str: JSON-formatted string containing extracted article data.
        - list: List of all 'entry.link' values.
    """
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
        extracted_entry = {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "summary": entry.get("summary", ""),
            "published": entry.get("published", ""),
            "id": entry.get("id", "")
        }
        extracted_data.append(extracted_entry)

    # Create a dictionary for the extracted data
    result_dict = {"articles": extracted_data}

    # Convert the dictionary to a JSON string
    result_json = json.dumps(result_dict, indent=4)

    return result_json, all_links  # Return both the JSON and the list of entry.link values


if __name__ == "__main__":

    rss_feed_urls = [
        "https://feeds.a.dj.com/rss/RSSOpinion.xml",
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://feeds.a.dj.com/rss/RSSWSJD.xml",
        "https://feeds.a.dj.com/rss/RSSLifestyle.xml",
    ]

    result_json, all_links = extract_rss_article_data(rss_feed_urls)

    # Save the JSON to a file
    with open('rss_feed.json', 'w') as json_file:
        json_file.write(result_json)

    print(all_links[0:3])
