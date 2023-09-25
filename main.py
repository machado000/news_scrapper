'''
news_scrapper
v.2023-09-23
'''

import json

import feedparser
import openai
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # noqa

from src._drv_scrapers import CustomWebDriver


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


def login_wsj(driver):
    """
    Login to https://session.wsj.com and parse username and passord.

    Args:
    - Selenium Chrome webdriver object.

    Returns:
    - None.
    - Browser on logged state.
    """
    # Open the login page
    login_url = "https://session.wsj.com"
    username = "kbsquire"
    password = "poker"

    print(f"INFO  - Navigating to {login_url}")
    try:
        driver.get(login_url)
        print("INFO  - [Success]")
    except Exception as e:
        print(f"ERROR - Error navigating to {login_url}: ", e)
        raise Exception

    # First screen
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(username)

    continue_button = driver.find_element(By.CSS_SELECTOR, 'button[type="button"].solid-button.continue-submit.new-design')  # noqa
    continue_button.click()

    # Second screen
    password_field = driver.find_element(By.ID, "password-login-password")
    password_field.send_keys(password)

    login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"].solid-button.new-design.basic-login-submit')  # noqa
    login_button.click()

    return None


def fetch_page_source(driver, url):
    """
    Navigate to a url and save page_source as local html file.

    Args:
    - Selenium Chrome webdriver object.
    - Url to be saved

    Returns:
    - HTML page content.
    - Local file saved as "page_source.html".
    """
    print(f"INFO  - Navigating to {url}")
    try:
        driver.get(url)
        print("INFO  - [Success]")
    except Exception as e:
        print(f"ERROR - Error navigating to {url}: ", e)
        raise Exception

    # Parse the HTML content of the page using BeautifulSoup
    page_source = driver.page_source

    with open("page_source.html", "w", encoding="utf-8") as file:
        file.write(page_source)

    return page_source


if __name__ == "__main__":

    """
    1. Fetch urls from RSS feeds
    """
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

    """
    2. Open Selenium Chrome webdriver and login to WSJ
    """
    handler = CustomWebDriver()
    driver = handler.open_driver()
    driver.implicitly_wait(3)  # Adjust the wait time as needed

    login_wsj(driver)

    """
    3. Fetch and save page HTML source
    """
    # Fetch article text
    url = "https://www.wsj.com/articles/ipo-market-arm-instacart-klaviyo-stocks-ee65206?mod=rss_markets_main"

    page_source = fetch_page_source(driver, url)  # DEBUG check page_source.html

    # Close the driver when done
    driver.quit()

    """
    4. Extract article text from page HTML source
    """
    # TODO

    """
    5. Send article text to openai and fetch summary
    """
    api_key = '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'
    file_path = 'article.txt'

    with open(file_path, 'r') as file:
        input_text = file.read()

    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"Generate a coherent human-like 200 word summary of the following text:\n{input_text}",
        max_tokens=400,  # Adjust max_tokens for the desired length of the summary
        api_key=api_key
    )

    # print(response)  # DEBUG

    # Extract the generated summary and keywords
    summary = response.choices[0].text.strip()

    # Print the summary and keywords
    print("Summary:")
    print(summary)
