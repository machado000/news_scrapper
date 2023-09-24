'''
news_scrapper
v.2023-09-23
'''

import feedparser
import json
import pandas as pd  # noqa

from src._drv_scrapers import CustomRequests, CustomWebDriver  # noqa

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By  # noqa
from selenium.webdriver.common.keys import Keys  # noqa


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

    # rss_feed_urls = [
    #     "https://feeds.a.dj.com/rss/RSSOpinion.xml",
    #     "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    #     "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
    #     "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    #     "https://feeds.a.dj.com/rss/RSSWSJD.xml",
    #     "https://feeds.a.dj.com/rss/RSSLifestyle.xml",
    # ]

    # result_json, all_links = extract_rss_article_data(rss_feed_urls)

    # # Save the JSON to a file
    # with open('rss_feed.json', 'w') as json_file:
    #     json_file.write(result_json)

    # print(all_links[0:3])

    scraper = CustomWebDriver()
    driver = scraper.open_driver()
    driver.implicitly_wait(8)  # Adjust the wait time as needed

    # Open the login page
    login_url = "https://session.wsj.com"

    driver.get(login_url)

    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys("kbsquire")

    continue_button = driver.find_element(By.CSS_SELECTOR, 'button[type="button"].solid-button.continue-submit.new-design')  # noqa
    continue_button.click()

    password_field = driver.find_element(By.ID, "password-login-password")
    password_field.send_keys("poker")

    login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"].solid-button.new-design.basic-login-submit')  # noqa
    login_button.click()

    # Now, you are logged in. You can navigate to another URL
    driver.get("https://www.wsj.com/articles/ipo-market-arm-instacart-klaviyo-stocks-ee65206?mod=rss_markets_main")

    # Get the HTML content of the page
    page_source = driver.page_source

    with open("page_source.html", "w", encoding="utf-8") as file:
        file.write(page_source)

    # Close the driver when done
    driver.quit()

    # Parse the HTML content of the page using BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')

    # Find elements that are relevant for screen readers
    screen_reader_text = []

    # Examples: extracting text from <p>, <a>, and elements with aria-label
    for element in soup.find_all(['p', 'a', lambda tag: tag.has_attr('aria-label')]):
        text = element.get_text(strip=True)
        if text:
            screen_reader_text.append(text)

    # Print the extracted text
    for text in screen_reader_text:
        print(text)
