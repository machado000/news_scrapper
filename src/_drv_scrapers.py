"""
This class is used to scrap web pages by fetching content using proxies and random user agents for anonymity.
It uses package `requests` to provide methods for retrieving responses with `.get_response` or
get HTML soup object with `.fetch_soup`.
It also use package `selenium` to initialize a webdriver and provide methods `.open_driver`, `.navigate` to url
and `.fecht_element` for further processing.
v.2023-09-05
"""
import os
import time
import zipfile

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

from src._decorators import retry


class CustomRequests:

    def __init__(self, username, password, endpoint, port):

        # proxy_auth = HTTPProxyAuth(username, password)
        proxy_url = f"http://{username}:{password}@{endpoint}:{port}"

        self.session = requests.Session()
        self.session.proxies = {'http': proxy_url, 'https': proxy_url}
        # self.session.auth = proxy_auth

        ua = UserAgent(
            browsers=["edge", "chrome", "firefox"],
            fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0"
        )

        self.session.headers.update({'User-Agent': ua.random})

    @retry()
    def get_response(self, url):
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            return response
        except Exception as e:
            print("INFO  - Failed to get response: ", e)
            raise Exception

    @retry()
    def fetch_soup(self, url):
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            soup = BeautifulSoup(response.text, "html.parser")
            return soup
        except Exception as e:
            print("INFO  - Failed to fetch soup: ", e)
            raise Exception

    @retry()
    def fetch_soup_lxml(self, url):
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            soup = BeautifulSoup(response.text, features="xml")
            return soup
        except Exception as e:
            print("INFO  - Failed to fetch soup: ", e)
            raise Exception

    @retry()
    def save_soup_as_html(self, soup, filename):
        try:
            if soup:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(soup.prettify())
                print(f"INFO  - HTML content saved as '{filename}'")
                return True
        except Exception as e:
            print("ERROR - Unable to save HTML content: ", e)
            raise Exception


class CustomWebDriver:

    def __init__(self, username=None, password=None, endpoint=None, port=None):

        self.ua = UserAgent(
            browsers=["edge", "chrome", "firefox"],
            os=["windows", "macos"],
            min_percentage=0.03,
            fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0"
        )

        self.proxies_extension = self.proxies(username, password, endpoint, port)

        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument("--headless=new")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument("--ignore-ssl-errors")
        self.chrome_options.add_argument("--window-size=1920,1200")
        self.chrome_options.add_argument(f"--user-agent={self.ua.random}")
        self.chrome_options.add_extension(self.proxies_extension)
        self.driver = None

        # print(self.chrome_options.to_capabilities()) # DEBUG

    @retry()
    def open_driver(self):
        try:
            # self.driver = webdriver.Chrome(options=self.chrome_options)
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.chrome_options)  # noqa
            width = self.driver.get_window_size().get("width")
            height = self.driver.get_window_size().get("height")
            # self.driver.implicitly_wait(0.5)
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            self.driver.get("https://ipinfo.io/ip")
            body_element = self.driver.find_element(By.TAG_NAME, "body")
            external_ip = body_element.text

            print("INFO  - Opened a Chrome driver window with settings:",
                  f"INFO  - UA: {user_agent}",
                  f"INFO  - Proxy IPv4: {external_ip}",
                  f"INFO  - Window size: {width}x{height}",
                  sep="\n")
            return self.driver

        except Exception as e:
            print("ERROR - Could not initialize driver: ", e)
            raise Exception

    @retry()
    def navigate(self, url):
        print(f"INFO  - Navigating to {url}")
        try:
            self.driver.get(url)
            print("INFO  - [Success]")
        except Exception as e:
            print(f"ERROR - Error navigating to {url}: ", e)
            raise Exception

    @retry()
    def fetch_element(self, css_selector):
        print(f"INFO  - Fetching elements with selector: {css_selector[0:41]}")
        try:
            # elements = WebDriverWait(self.driver, timeout).until(
            #     EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            # )
            elements = self.driver.find_elements(By.CSS_SELECTOR, value=css_selector)
            return elements
        except Exception as e:
            print(f"ERROR - Could not find element {css_selector}: ", e)

        return []

    @retry()
    def infinite_scroll(self, scroll_pause_time=10, end_scroll_attempts=3):
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        # footer = self.driver.find_element(By.CSS_SELECTOR, "div.footerstyles__Footer-sc-1ar2w9j-0.jdgzxt")
        # ActionChains(self.driver).scroll_to_element(footer).perform()
        print(f"INFO  - Window opened with content height of {last_height}")
        # self.driver.save_screenshot(f'./screenshot_{last_height}.png')  # DEBUG

        attempts = 0

        while attempts < end_scroll_attempts:

            for _ in range(3):
                # press PAGE_DOWN or SCROLL 3 times
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                time.sleep(3)  # time between key presses / scrolls

            # ActionChains(self.driver).scroll_by_amount(0, 600).perform()
            time.sleep(scroll_pause_time)  # Wait for aditional content to load

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            # self.driver.save_screenshot(f'./screenshot_{new_height}.png')  # DEBUG

            if new_height == last_height:
                attempts += 1
                print(f"INFO  - Could not load new content (retry {attempts}/{end_scroll_attempts})")
            else:
                attempts = 0  # Reset attempts if scroll height changes

            last_height = new_height
            print(f"INFO  - Scroll down to height {new_height}")

        print("INFO  - Page seems to be fully loaded")

    @retry()
    def close_driver(self):
        try:
            self.driver.close()
            print("INFO  - Closed driver window")
            return True
        except Exception as e:
            print("ERROR - Error closing driver: ", e)
            raise Exception

    def proxies(self, username, password, endpoint, port):
        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Proxies",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """

        background_js = """
        var config = {
                mode: "fixed_servers",
                rules: {
                singleProxy: {
                    scheme: "http",
                    host: "%s",
                    port: parseInt(%s)
                },
                bypassList: ["localhost"]
                }
            };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "%s",
                    password: "%s"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ["<all_urls>"]},
                    ['blocking']
        );
        """ % (endpoint, port, username, password)

        extension = 'proxies_extension.zip'

        with zipfile.ZipFile(extension, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)

        return extension


def test_custom_requests(username, password, endpoint, port):
    # url_to_scrape = "https://www.scrapethissite.com/pages/simple/"
    url_to_scrape = "https://ipinfo.io/ip"

    try:
        scraper = CustomRequests(username, password, endpoint, port)
        # scraper.test_proxies()
        soup = scraper.fetch_soup(url_to_scrape)
        print(f"INFO  - Success fetching response from '{url_to_scrape}'")
        print(f"Proxy: {soup.text}")

    except Exception as e:
        print("ERROR - Unable to fetch response: ", e)


def test_custom_webdriver(username, password, endpoint, port):
    url_to_scrape = "https://browsersize.com/"

    try:
        scraper = CustomWebDriver(username, password, endpoint, port)
        # scraper.test_proxies()
        scraper.open_driver()
        scraper.navigate(url_to_scrape)
        scraper.driver.save_screenshot('./screenshot.png')
        print("INFO  - Saved screenshot image at './screenshot.png'")
        scraper.close_driver()
    except Exception as e:
        print("ERROR - ", e)


if __name__ == "__main__":

    load_dotenv()
    username = os.getenv('PROXY_USERNAME')
    password = os.getenv('PROXY_PASSWORD')
    endpoint = os.getenv('PROXY_SERVER')
    port = os.getenv('PROXY_PORT')
    # proxy_string = f"http://{username}:{password}@{endpoint}:{port}"
    # print(proxy_string)

    test_custom_requests(username, password, endpoint, port)

    test_custom_webdriver(username, password, endpoint, port)
