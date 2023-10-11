'''
news_scrapper
v.2023-10-02
'''
import json
import os
import re
import string
import sys
from datetime import datetime, timedelta
from time import sleep

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import random  # noqa
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src._decorators import retry
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

html_files_path, json_files_path = "./html_files", "./json_files"
[os.makedirs(path) for path in [html_files_path, json_files_path] if not os.path.exists(path)]


def clean_text(text_str):
    text_str = re.sub(r'\n', ' ', text_str)
    text_str = ' '.join(text_str.split())

    valid_chars = set(string.printable)
    cleaned_text = ''.join(char for char in text_str if char in valid_chars)

    return cleaned_text


def get_redirected_url(url):
    custom_requests = CustomRequests(proxy_username, proxy_password, proxy_server, proxy_port)
    response = custom_requests.get_response(url)
    redirected_url = response.url
    return redirected_url


@retry()
def login_financialtimes(driver):
    """
    Login to https://accounts.ft.com/login and parse username and passord.

    Args:
    - driver (object) Selenium Chromium webdriver object.

    Returns:
    - None.
    - Browser on logged state.
    """
    # Open the login page
    login_url = "https://accounts.ft.com/login"
    # mongo_cnx = MongoCnx("news_db")
    username = "ksquire@icomm-net.com"
    password = "financialtimes13d"

    print(f"INFO  - Navigating to {login_url}")
    driver.get(login_url)

    try:
        element_present = EC.presence_of_element_located((By.ID, "enter-email-next"))
        WebDriverWait(driver=driver, timeout=20).until(element_present)
        print("INFO  - Page fully loaded!")
    except TimeoutException:
        print("ERROR - Timed out waiting for page to load")

    # First screen
    username_field = driver.find_element(By.ID, "enter-email")
    username_field.send_keys(username)

    continue_button = driver.find_element(By.ID, 'enter-email-next')
    continue_button.click()

    # Second screen
    sleep(2)
    password_field = driver.find_element(By.ID, 'enter-password')
    # By.CSS_SELECTOR, 'input#enter-email[type="email"][name="email"][placeholder="Enter your email address"]')
    password_field.send_keys(password)

    login_button = driver.find_element(By.ID, 'sign-in-button')
    login_button.click()

    # try:
    #     element_present = EC.presence_of_element_located(
    #         (By.CSS_SELECTOR, 'a.o-header__subnav-link[data-trackable="Sign Out"]'))
    #     WebDriverWait(driver=driver, timeout=40).until(element_present)
    #     print("INFO  - Button 'SIGN OUT' was found on page \nINFO  - Login with success !")
    # except TimeoutException:
    #     print("ERROR - Timed out waiting for page to load")
    # except NoSuchElementException:
    #     print("ERROR - Button 'SIGN OUT' not found on page")

    return None


@retry()
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


@retry()
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

    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")

    # Extract TXT from article body
    collection = mongo_cnx.db["selectors"]
    selector = collection.find_one({"domain": domain})

    if selector["selector"] == "element":
        element = soup.find(selector["element"])

    if selector["selector"] == "class":
        # element = soup.find(selector["element"], class_=selector["class"])
        element_list = soup.select(f'{selector["element"]}[class*="{selector["class"]}"]')
        element = element_list[0]

    if selector["selector"] == "id":
        element = soup.find(selector["element"], id=selector["id"])

    if selector["selector"] == "data-test":
        element = soup.find(selector["element"], attrs={"data-test": selector["data-test"]})

    cleaned_text = clean_text(element.text)

    return cleaned_text


def parse_ft_webpages(driver, collection_name, days_ago=2, status="fetched"):

    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")
    date_obj = datetime.now() - timedelta(days=days_ago)
    start_publish_date = date_obj.isoformat()
    domain = "ft.com"

    # 1. list articles to be scraped
    articles = mongo_cnx.get_doc_list(collection_name=collection_name, domain=domain,
                                      start_publish_date=start_publish_date, status=status)

    if articles == []:
        print("INFO  - Exiting program. No documents where found.")
        sys.exit()

    print("INFO  - Last document _id:", articles[-1]["_id"], ", publish_date:",
          articles[-1]["publish_date"], "url:", articles[-1]["url"])

    # 3-A. Login to Wall Street (Journal WSJ)
    # login_financialtimes(driver)

    # 3-B. Fetch and save page HTML soup and article_body.text
    articles_contents = []
    total_count = len(articles)
    # item = articles[-1]

    for idx, item in enumerate(articles, start=1):
        try:
            file_path = f"{html_files_path}/{item['_id']}.html"

            if os.path.exists(file_path):
                print(f"INFO  - Found page source on {file_path}")

                with open(file_path, "r", encoding="utf-8") as html_file:
                    html_content = html_file.read()
                soup = BeautifulSoup(html_content, 'html.parser')

            else:
                # Fetch page
                soup = fetch_page_soup(driver, item["url"])

                # Save local HTML file
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(soup.prettify())
                print(f"INFO  - Saved page source on {file_path}")

            # Extract TXT from article body
            article_body_element = soup.find(By.ID, "article-body")
            article_element = soup.find("article")
            section_element = soup.find("section")

            if article_element and article_element.text:
                article_body_text = article_element.text
                print("INFO  - article_body_text:", article_body_text[0:300])

            elif article_body_element and article_body_element.text:
                article_body_text = article_body_element.text
                print("INFO  - article_body_text:", article_body_text[0:300])

            elif section_element and section_element.text:
                article_body_text = section_element.text
                print("INFO  - article_body_text:", article_body_text[0:300])

            else:
                print(f"ERROR - Cant find article element on page source {item['_id']}.html ")

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

    with open(f"{json_files_path}/articles_contents.json", "w", encoding="utf-8") as json_file:
        json.dump(articles_contents, json_file)

    # 4. Update Mongodb with new article summaries
    with open(f"{json_files_path}/articles_contents.json", "r", encoding="utf-8") as json_file:
        articles_contents = json.load(json_file)

    mongo_cnx.update_collection(collection_name, articles_contents)


def parse_wsj_webpages(driver, collection_name, days_ago=2, status="fetched"):

    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")
    date_obj = datetime.now() - timedelta(days=days_ago)
    start_publish_date = date_obj.isoformat()
    domain = "wsj.com"

    # 1. list articles to be scraped
    articles = mongo_cnx.get_doc_list(collection_name=collection_name, domain=domain,
                                      start_publish_date=start_publish_date, status=status)

    if articles == []:
        print("INFO  - Passing. No documents where found with WSJ source.")
        return None

    print("INFO  - Last document _id:", articles[-1]["_id"], ", publish_date:", articles[-1]["publish_date"])

    # 3-A. Login to Wall Street (Journal WSJ)
    login_wsj(driver)

    # 3-B. Fetch and save page HTML soup and article_body.text
    articles_contents = []
    total_count = len(articles)

    for idx, item in enumerate(articles, start=1):
        try:
            file_path = f"{html_files_path}/{item['_id']}.html"

            if os.path.exists(file_path):
                print(f"INFO  - Found page source on {file_path}")

                with open(file_path, "r", encoding="utf-8") as html_file:
                    html_content = html_file.read()
                soup = BeautifulSoup(html_content, 'html.parser')

            else:
                # Fetch page
                soup = fetch_page_soup(driver, item["url"])

                # Save local HTML file
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(soup.prettify())
                print(f"INFO  - Saved page source on {file_path}")

            # Extract TXT from article body
            article_element = soup.find("article")
            section_element = soup.find("section")

            if article_element and article_element.text:
                article_body_text = article_element.text
                print("INFO  - article_body_text:", article_body_text[0:300])

            elif section_element and section_element.text:
                article_body_text = section_element.text
                print("INFO  - article_body_text:", article_body_text[0:300])

            else:
                print(f"ERROR - Cant find article element on page source {item['_id']}.html ")

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

    with open(f"{json_files_path}/articles_contents.json", "w", encoding="utf-8") as json_file:
        json.dump(articles_contents, json_file)

    # 4. Update Mongodb with new article summaries
    with open(f"{json_files_path}/articles_contents.json", "r", encoding="utf-8") as json_file:
        articles_contents = json.load(json_file)

    mongo_cnx.update_collection(collection_name, articles_contents)


def parse_free_webpages(start_publish_date, domain=None):

    # 0. Initial settings
    mongo_cnx = MongoCnx("news_db")

    # 1. list articles to be scraped
    collection_name = "news"
    domain = "www.msn.com"  # DEBUG
    start_publish_date = datetime.now() - timedelta(days=2)  # DEBUG
    status = "fetched"
    articles = mongo_cnx.get_doc_list(collection_name=collection_name, domain=domain,
                                      start_publish_date=start_publish_date, status=status)

    if articles == []:
        print(f"INFO  - Finishing task. No documents where found with domain {domain} and status {status}.")
        return None

    print("INFO  - Last document _id:", articles[-1]["_id"], ", publish_date:", articles[-1]["publish_date"])

    # 2. Start Selenium Chrome Webdriver
    handler = CustomWebDriver(username=proxy_username, password=proxy_password,
                              endpoint=proxy_server, port=proxy_port)
    driver = handler.open_driver()

    # 3. Fetch and save page HTML soup and article_body.text
    articles_contents = []
    total_count = len(articles)
    item = articles[0]  # DEBUG
    print("DEBUG - ", item)

    for idx, item in enumerate(articles, start=1):
        try:
            soup = fetch_page_soup(driver, item["url"])
            # print("DEBUG - ", soup.prettify())

            session = CustomRequests(proxy_username, proxy_password, proxy_server, proxy_port)
            soup = session.fetch_soup(item["url"])

            # Save local HTML file
            html_file_path = f"{html_files_path}/{item['_id']}.html"
            with open(html_file_path, "w", encoding="utf-8") as file:
                file.write(soup.prettify())

            # Extract TXT from article body
            collection = mongo_cnx.db["selectors"]  # DEBUG
            selector = collection.find_one({"domain": domain})  # DEBUG
            print(selector)  # DEBUG

            element = soup.find("article")  # DEBIG
            article_body_text = element.text  # DEBUG
            article_body_text = parse_article_text(soup=soup, domain=item['domain'])
            print(f"DEBUG - article_body_text: {article_body_text[0:500]}...")

            content_entry = {
                "_id": item['_id'],
                "content": article_body_text,
                "status": "content_parsed",
            }

            articles_contents.append(content_entry)

            print(f"INFO  - {idx}/{total_count} articles fetched and parsed.")

        # except IndexError as e:
        #     print(f"ERROR - {idx}/{total_count} - Error parsing {item['url']}: {str(e)}")

        #     content_entry = {
        #         "_id": item['_id'],
        #         "status": "error_parse_content",
        #     }
        #     articles_contents.append(content_entry)
        #     continue  # Continue to the next item in case of an error

        except Exception as e:
            print(f"ERROR - {idx}/{total_count} - Error parsing {item['url']}: {str(e)}")
            continue  # Continue to the next item in case of an error

    with open(f"{json_files_path}/articles_contents.json", "w", encoding="utf-8") as json_file:
        json.dump(articles_contents, json_file)

    # 4. Update Mongodb with new article summaries
    with open(f"{json_files_path}/articles_contents.json", "r", encoding="utf-8") as json_file:
        articles_contents = json.load(json_file)

    mongo_cnx.update_collection("news", articles_contents)


if __name__ == "__main__":

    handler = CustomWebDriver(username=proxy_username, password=proxy_password,
                              endpoint=proxy_server, port=proxy_port)
    driver = handler.open_driver()

    collection_name = "news_unprocessed"
    days_ago = 10
    status = "fetched"

    # Parse WSJ
    parse_wsj_webpages(driver=driver, collection_name=collection_name, days_ago=days_ago, status=status)

    # Parse Financial Times
    login_financialtimes(driver)

    parse_ft_webpages(driver=driver, collection_name=collection_name, days_ago=days_ago, status=status)

    # # Parse FREE news_sites
    # valid_domains = [
    #     "www.msn.com",
    #     # "markets.businessinsider.com",
    #     # "www.insidermonkey.com",
    #     # "www.nasdaq.com",
    #     # "www.thestreet.com",
    #     # "www.morningstar.com",
    # ]

    # for domain in valid_domains:
    #     print(f"\nINFO  - Parsing domain {domain}")
    #     parse_free_webpages(start_publish_date=days_ago, domain=domain)
