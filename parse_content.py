'''
news_scrapper
v.2023-09-23
'''
import json
import os
from time import sleep

from datetime import datetime
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
        print(f"\nINFO  - Navigating to {url}")
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


def parse_article_text(soup, domain):
    # Extract TXT from article body
    collection = mongo_cnx.db["selectors"]
    element_selector = collection.find_one({"domain": domain})
    # print("DEBUG - selector: ", selector["element"])

    if element_selector["selector"] == "element":
        element = soup.find(element_selector["element"])

    if element_selector["selector"] == "class":
        element = soup.find(element_selector["element"], class_=element_selector["class"])

    if element_selector["selector"] == "id":
        element = soup.find(element_selector["element"], id=element_selector["id"])

    if element_selector["selector"] == "data-test":
        element = soup.find(element_selector["element"], attrs={"data-test": element_selector["data-test"]})

    article_body_text = element.text

    return article_body_text


if __name__ == "__main__":

    # 0. Initial settings
    files_path = "./news_data"
    if not os.path.exists(files_path):
        os.makedirs(files_path)

    mongo_cnx = MongoCnx("news_db")

    # 1. list articles to be scraped
    collection_name = "news"
    domain = "www.wsj.com"
    start_date = datetime(2023, 10, 1, 12, 00)
    status = "fetched"
    articles = mongo_cnx.get_doc_list(collection_name, domain, start_date, status)
    print("INFO  - Last document: ", articles[-1:])

    # 2. Start Selenium Chrome Webdriver
    handler = CustomWebDriver(username=proxy_username, password=proxy_password,
                              endpoint=proxy_server, port=proxy_port)
    driver = handler.open_driver()

    # 3-A. Login to Wall Street (Journal WSJ)
    login_wsj(driver)

    # 3-B. Fetch and save page HTML soup and article_body.text
    articles_contents = []
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

            content_entry = {
                "_id": item['_id'],
                "content": article_body_text,
                "status": "content_parsed",
            }

            articles_contents.append(content_entry)

            print(f"INFO  - {idx}/{total_count} articles fetched and parsed content.")

        except Exception as e:
            print(f"ERROR - {idx}/{total_count} - Error fetching {item['url']}: {str(e)}")
            continue  # Continue to the next item in case of an error

    with open(f"./{files_path}/articles_contents.json", "w", encoding="utf-8") as json_file:
        json.dump(articles_contents, json_file)

    # 4. Update Mongodb with new article summaries
    mongo_cnx.update_collection("news", articles_contents)

    # Close the driver when done
    # driver.quit()
