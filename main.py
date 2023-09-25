'''
news_scrapper
v.2023-09-23
'''

# import codecs
import json
import os

import feedparser
import openai
from bs4 import BeautifulSoup  # noqa
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # noqa

from src._drv_scrapers import CustomRequests, CustomWebDriver   # noqa

# Load variables from .env
load_dotenv()
proxy_username = os.getenv('PROXY_USERNAME')
proxy_password = os.getenv('PROXY_PASSWORD')
proxy_server = os.getenv('PROXY_SERVER')
proxy_port = os.getenv('PROXY_PORT')
wsj_username = os.getenv('WSJ_USERNAME')
wsj_password = os.getenv('WSJ_PASSWORD')
bing_apikey = os.getenv('BING_APIKEY')
openai_apikey = os.getenv('OPENAI_APIKEY')
# print(proxy_username, proxy_password, proxy_server, proxy_port, wsj_username, wsj_password, bing_apikey, openai_apikey)  # noqa

files_path = "./files"

if not os.path.exists(files_path):
    os.makedirs(files_path)


def request_bing_news(session, query, category="Business", results_count=100, freshness="day"):

    url = "https://api.bing.microsoft.com/v7.0/news/search"

    params = {
        "q": query,
        "category": category,
        "count": results_count,
        "freshness": freshness,
        "mkt": "en-US",
        "setLang": "en"
    }

    headers = {
        "Ocp-Apim-Subscription-Key": bing_apikey
    }

    # Make the API request
    response = session.get(url, params=params, headers=headers)

    if response.status_code == 200:
        response_data = response.json()

        results = []
        all_links = []

        for value in response_data["value"]:
            extracted_entry = {
                "title": value.get("name", ""),
                "link": value.get("url", ""),
                "summary": value.get("description", ""),
                "published": value.get("datePublished", ""),
            }
            results.append(extracted_entry)

            all_links.append(value.get("url", ""))

        # Create a dictionary for the extracted data
        result_dict = {"articles": results}

        # Convert the dictionary to a JSON string
        result_json = json.dumps(result_dict, indent=4)

        return result_json, all_links  # Return both the JSON and the list of entry.link values


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
    result_json = json.dumps(result_dict, ensure_ascii=False, indent=4)

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
    username = wsj_username
    password = wsj_password

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
    Navigate to a url and fetch page_source.

    Args:
    - Selenium Chrome webdriver object.
    - Url to be saved

    Returns:
    - HTML page content.
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

    return page_source


if __name__ == "__main__":

    try:
        """
        A-1. Fetch urls from RSS feeds
        """
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
        with open('./files/rss_feed.json', 'w', encoding='utf-8') as file:
            file.write(result_json)

        print(all_links[0])

    #     """
    #     A-2. Open Selenium Chrome webdriver and login to WSJ
    #     """
    #     handler = CustomWebDriver(username=proxy_username, password=proxy_password,
    #                               endpoint=proxy_server, port=proxy_port)
    #     driver = handler.open_driver()
    #     driver.implicitly_wait(3)  # Adjust the wait time as needed

    #     login_wsj(driver)

    #     """
    #     A-3. Fetch and save page HTML source
    #     """
    #     # Fetch article text
    #     # url = "https://www.wsj.com/articles/ipo-market-arm-instacart-klaviyo-stocks-ee65206?mod=rss_markets_main"
    #     url = all_links[0]

    #     page_source = fetch_page_source(driver, url)  # DEBUG check page_source.html

    #     # Parse the HTML content with BeautifulSoup
    #     soup = BeautifulSoup(page_source, 'html.parser')

    #     with open('./files/page_source.html', 'w', encoding="utf-8") as file:
    #         file.write(soup.prettify())

    #     # Close the driver when done
    #     driver.quit()

    #     """
    #     A-4. Extract article text from page HTML source
    #     """
    #     # TODO

    except Exception as e:
        print("ERROR - ", e)

    """
    B-1. Fetch urls from Bing API
    """
    handler = CustomRequests(username=proxy_username, password=proxy_password, endpoint=proxy_server, port=proxy_port)
    session = handler.session
    soup = handler.fetch_soup("https://ipinfo.io/ip")
    print(f"INFO  - Success opening session with proxy ip '{soup.text}'")

    query = '"Activist investor" | "Carl Icahn" | "corporate governance" | "universal proxy" | "13D Monitor" | "Schedule 13D"'  # noqa

    response_json, all_links = request_bing_news(session, query, results_count=100, freshness="month")

    with open('./files/bing_news_results.json', 'w', encoding='utf-8') as file:
        file.write(response_json)

    # print(response_json)
    print(all_links[0:3])

    """
    5. Send article text to openai and fetch summary
    """
    api_key = openai_apikey
    file_path = './files/article.txt'

    with open(file_path, 'r', encoding='utf-8') as file:
        input_text = file.read()

    # print(input_text) # DEBUG

    prompt = f"Using a style suitable for business reports compose a 200-word summary of the following text:\n{input_text}."  # noqa

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=400,  # Adjust max_tokens for the desired length of the summary
        api_key=api_key
    )

    # print(response)  # DEBUG

    # Extract the generated summary and keywords
    summary = response.choices[0].text.strip()

    # Print the summary and keywords
    print("Summary:")
    print(summary)
