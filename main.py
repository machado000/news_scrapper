'''
news_scrapper
v.2023-09-23
'''

import feedparser
import json
import pandas as pd

import src._decorators  # noqa
import src._drv_scrapers  # noqa


rss_feed_urls = [
    "https://feeds.a.dj.com/rss/RSSOpinion.xml",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://feeds.a.dj.com/rss/RSSWSJD.xml",
    "https://feeds.a.dj.com/rss/RSSLifestyle.xml",
]


# Create an empty list to store feed data
all_entries = []

# Loop through the list of feed URLs
for rss_feed_url in rss_feed_urls:
    # Parse the RSS feed
    feed = feedparser.parse(rss_feed_url)

    # Append the feed data to the list
    all_entries.extend(feed.entries)

# Create a dictionary containing only the "entries" key
result_data = {"entries": all_entries}

# Convert the dictionary to a JSON string
result_json = json.dumps(result_data, indent=4)

# Save the JSON to a file
with open('rss_feed.json', 'w') as json_file:
    json_file.write(result_json)
