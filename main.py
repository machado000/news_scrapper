'''
news_scrapper
v.2023-09-23
'''
import json
import os
from time import sleep

import openai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src._drv_mongodb import MongoCnx
from src._drv_scrapers import CustomRequests, CustomWebDriver

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
# print("DEBUG - ", proxy_username, proxy_password, proxy_server, proxy_port, wsj_username, wsj_password, bing_apikey, openai_apikey) # noqa


def get_redirected_url(url):
    custom_requests = CustomRequests(proxy_username, proxy_password, proxy_server, proxy_port)
    response = custom_requests.get_response(url)
    redirected_url = response.url
    return redirected_url


def login_wsj(driver):
    """
    Login to https://session.wsj.com and parse username and passord.

    Args:
    - driver (object) Selenium Chromium webdriver object.

    Returns:
    - None.
    - Browser on logged state.
    """
    # Open the login page
    login_url = "https://session.wsj.com"
    username = wsj_username
    password = wsj_password

    print(f"INFO  - Navigating to {login_url}")
    driver.get(login_url)

    try:
        element_present = EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'button[type="button"].solid-button.continue-submit.new-design'))
        WebDriverWait(driver=driver, timeout=20).until(element_present)
        print("INFO  - Page fully loaded!")
    except TimeoutException:
        print("ERROR - Timed out waiting for page to load")

    # First screen
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(username)

    continue_button = driver.find_element(
        By.CSS_SELECTOR, 'button[type="button"].solid-button.continue-submit.new-design')
    continue_button.click()

    # Second screen
    sleep(2)
    password_field = driver.find_element(By.ID, "password-login-password")
    password_field.send_keys(password)

    login_button = driver.find_element(
        By.CSS_SELECTOR, 'button[type="submit"].solid-button.new-design.basic-login-submit')
    login_button.click()

    try:
        element_present = EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'div.sc-dIfARi.kNNa-dS button.btn.btn--primary[type="button"]'))
        WebDriverWait(driver=driver, timeout=40).until(element_present)
        print("INFO  - Button 'SIGN OUT' was found on page \nINFO  - Login with success !")
    except TimeoutException:
        print("ERROR - Timed out waiting for page to load")
    except NoSuchElementException:
        print("ERROR - Button 'SIGN OUT' not found on page")

    return None


def fetch_page_soup(driver, url):
    """
    Navigate to a url and fetch page_source.

    Args:
    - driver (object) Selenium Chrome webdriver object.
    - url (str) URL to be saved

    Returns:
    - HTML page content.
    """
    try:
        print(f"INFO  - Navigating to {url}")
        driver.get(url)

        body_element = EC.presence_of_element_located((By.TAG_NAME, "body"))
        WebDriverWait(driver, 20).until(body_element)
        print("INFO  - Page <body> was loaded!")

        # Parse the HTML content of the page using BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        if soup:
            print("INFO  - Fetched BeautifulSoup HTML content")

        return soup

    except TimeoutException:
        print("ERROR - Timed out waiting for page to load")
        raise Exception


def fetch_article_text(soup, domain):
    # Extract TXT from article body
    collection = mongo_cnx.db["selectors"]
    selector_parameters = collection.find_one({"domain": domain})
    # print("DEBUG - selector: ", selector["element"])

    if selector_parameters["selector"] == "element":
        article_body = soup.find(selector["element"])

    if selector_parameters["selector"] == "class":
        article_body = soup.find(selector["element"])

    article_body_text = article_body.text

    return article_body_text


def openai_summarize_text(input_text):
    try:
        print("INFO  - Querying OpenAI for article text summary.")

        openai.api_key = os.getenv('OPENAI_APIKEY')

        system_prompt = "Use a style suitable for business reports. Direct text to investors and business analysts. Write a single text block with no linkebreaks."  # noqa
        user_prompt_1 = f"Compose a 150-word summary of the following news article text: '{input_text}'"  # noqa

        response_1 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_1}
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
    domain = "www.wsj.com"
    start_date = "2022-01-01T00:00"

    articles = mongo_cnx.get_docs_by_domain_and_date(collection_name, domain, start_date, summarized=False)
    print("INFO  - Last document: ", articles[-3:])

    # 2. Start Selenium Chrome Webdriver
    handler = CustomWebDriver(username=proxy_username, password=proxy_password,
                              endpoint=proxy_server, port=proxy_port)
    driver = handler.open_driver()

    # 3-A. Login to Wall Street (Journal WSJ)
    login_wsj(driver)

    # 3-B. Fetch and save page HTML soup and article_body.text, generate article summary with OpenAI
    articles_summaries = []
    total_count = len(articles)

    for idx, item in enumerate(articles, start=1):
        try:
            soup = fetch_page_soup(driver, item["url"])

            # Save local HTML file
            html_file_path = f"./{files_path}/{item['_id']}.html"
            with open(html_file_path, "w", encoding="utf-8") as file:
                file.write(soup.prettify())

            # Extract TXT from article body
            collection = mongo_cnx.db["selectors"]
            selector = collection.find_one({"domain": item['domain']})
            # print("DEBUG - selector: ", selector["element"])

            if selector["selector"] == "element":
                article_body = soup.find(selector["element"])

            article_body_text = article_body.text

            # Save local TXT file
            txt_file_path = f"./{files_path}/{item['_id']}.txt"
            with open(txt_file_path, "w", encoding="utf-8") as file:
                file.write(article_body_text)

            # Send article text to openai and fetch summary
            summary = openai_summarize_text(article_body.text)

            summary_entry = {
                "_id": item['_id'],
                "openai_summary": summary,
                "summarized": True,
            }

            articles_summaries.append(summary_entry)
            print(f"INFO  - {idx}/{total_count} articles fetched and summarized.")

        except Exception as e:
            print(f"ERROR - {idx}/{total_count} - Error fetching {item['url']}: {str(e)}")
            continue  # Continue to the next item in case of an error

    with open(f"./{files_path}/articles_summaries.json", "w", encoding="utf-8") as json_file:
        json.dump(articles_summaries, json_file)

    # 4. Update Mongodb with new article summaries
    mongo_cnx.update_collection("news", articles_summaries)

    # Close the driver when done
    # driver.quit()
