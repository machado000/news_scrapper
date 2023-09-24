"""
This class is used to scrap web pages by fetching content using proxies and random user agents for anonymity.
It uses package `requests` to provide methods for retrieving responses with `.get_response` or
get HTML soup object with `.fetch_soup`.
It also use package `selenium` to initialize a webdriver and provide methods `.open_browser`, `.navigate` to url
and `.fecht_element` for further processing.
v.2023-09-05
"""
import random
import requests
import time

from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from selenium import webdriver
# from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait

from ._decorators import retry


class CustomRequests:

    def __init__(self, proxy_list=None):
        self.proxy_list = proxy_list or [
            "http://196.51.132.133:8800",
            "http://196.51.129.230:8800",
            "http://196.51.135.162:8800",
            "http://196.51.129.252:8800"
        ]

        self.ua = UserAgent(
            browsers=["edge", "chrome", "firefox"],
            fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0"
        )

    def test_proxies(self, timeout=5):
        print("INFO  - Testing available proxy servers")
        working_proxies = []

        for proxy in self.proxy_list:
            proxies = {"http": proxy, "https": proxy}
            try:
                response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=timeout)
                if response.status_code == 200:
                    working_proxies.append(proxy)
                    soup = BeautifulSoup(response.text, "html.parser")
                    element = eval(soup.text)
                    print(f"INFO  - [OK] Proxy {proxy} response 200 -- external IP ", element['origin'])
            except Exception as e:
                print(f"ERROR - Proxy {proxy} failed to respond: ", e)

        self.proxy_list = working_proxies

    @retry()
    def get_response(self, url):
        try:
            proxy = random.choice(self.proxy_list)
            proxies = {"http": proxy, "https": proxy}

            response = requests.get(url, headers={"User-Agent": self.ua.random}, proxies=proxies, timeout=5)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
        except Exception as e:
            print("INFO  - Failed to get response: ", e)
            raise Exception

    @retry()
    def fetch_soup(self, url):
        try:
            proxy = random.choice(self.proxy_list)
            proxies = {"http": proxy, "https": proxy}

            response = requests.get(url, headers={"User-Agent": self.ua.random}, proxies=proxies, timeout=5)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            soup = BeautifulSoup(response.text, "html.parser")
            return soup
        except Exception as e:
            print("INFO  - Failed to fetch soup: ", e)
            raise Exception

    @retry()
    def fetch_soup_lxml(self, url):
        try:
            proxy = random.choice(self.proxy_list)
            proxies = {"http": proxy, "https": proxy}

            response = requests.get(url, headers={"User-Agent": self.ua.random}, proxies=proxies, timeout=5)
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

    def __init__(self, proxy_list=None):
        self.proxy_list = proxy_list or [
            "http://196.51.129.230:8800",
            "http://196.51.129.252:8800",
            "http://196.51.132.133:8800",
            "http://196.51.135.162:8800",
        ]

        self.ua = UserAgent(
            browsers=["edge", "chrome", "firefox"],
            os=["windows", "macos"],
            min_percentage=0.03,
            fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0"
        )

        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless=new")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument("--ignore-ssl-errors")
        self.chrome_options.add_argument("--window-size=1920,1030")
        self.chrome_options.add_argument(f"--user-agent={self.ua.random}")
        self.chrome_options.add_argument(f"--proxy-server={random.choice(self.proxy_list)}")
        self.browser = None

    def test_proxies(self, timeout=5):
        print("INFO  - Testing available proxy servers")
        working_proxies = []

        for proxy in self.proxy_list:
            proxies = {"http": proxy, "https": proxy}
            try:
                response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=timeout)
                if response.status_code == 200:
                    working_proxies.append(proxy)
                    soup = BeautifulSoup(response.text, "html.parser")
                    element = eval(soup.text)
                    print(f"INFO  - [OK] Proxy {proxy} response 200 -- external IP ", element['origin'])
            except Exception as e:
                print(f"ERROR - Proxy {proxy} failed to respond: ", e)

        self.proxy_list = working_proxies

    @retry()
    def open_browser(self):
        try:
            self.browser = webdriver.Chrome(options=self.chrome_options)
            width = self.browser.get_window_size().get("width")
            height = self.browser.get_window_size().get("height")
            # self.browser.implicitly_wait(0.5)
            user_agent = self.browser.execute_script("return navigator.userAgent;")
            self.browser.get("http://httpbin.org/ip")
            body_element = self.browser.find_element(By.TAG_NAME, "body")
            external_ip = eval(body_element.text)

            print("INFO  - Opened a Chrome browser window with settings:",
                  f"INFO  - UA: {user_agent}",
                  f"INFO  - Proxy IPv4: {external_ip['origin']}",
                  f"INFO  - Window size: {width}x{height}",
                  sep="\n")
            return True

        except Exception as e:
            print("ERROR - Could not initialize browser: ", e)
            raise Exception

    @retry()
    def navigate(self, url):
        print(f"INFO  - Navigating to {url}")
        try:
            self.browser.get(url)
            print("INFO  - [Success]")
        except Exception as e:
            print(f"ERROR - Error navigating to {url}: ", e)
            raise Exception

    @retry()
    def fetch_element(self, css_selector):
        print(f"INFO  - Fetching elements with selector: {css_selector[0:41]}")
        try:
            # elements = WebDriverWait(self.browser, timeout).until(
            #     EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            # )
            elements = self.browser.find_elements(By.CSS_SELECTOR, value=css_selector)
            return elements
        except Exception as e:
            print(f"ERROR - Could not find element {css_selector}: ", e)

        return []

    @retry()
    def infinite_scroll(self, scroll_pause_time=10, end_scroll_attempts=3):
        last_height = self.browser.execute_script("return document.body.scrollHeight")
        # footer = self.browser.find_element(By.CSS_SELECTOR, "div.footerstyles__Footer-sc-1ar2w9j-0.jdgzxt")
        # ActionChains(self.browser).scroll_to_element(footer).perform()
        print(f"INFO  - Window opened with content height of {last_height}")
        # self.browser.save_screenshot(f'./screenshot_{last_height}.png')  # DEBUG

        attempts = 0

        while attempts < end_scroll_attempts:

            for _ in range(3):
                # press PAGE_DOWN or SCROLL 3 times
                self.browser.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                time.sleep(3)  # time between key presses / scrolls

            # ActionChains(self.browser).scroll_by_amount(0, 600).perform()
            time.sleep(scroll_pause_time)  # Wait for aditional content to load

            new_height = self.browser.execute_script("return document.body.scrollHeight")
            # self.browser.save_screenshot(f'./screenshot_{new_height}.png')  # DEBUG

            if new_height == last_height:
                attempts += 1
                print(f"INFO  - Could not load new content (retry {attempts}/{end_scroll_attempts})")
            else:
                attempts = 0  # Reset attempts if scroll height changes

            last_height = new_height
            print(f"INFO  - Scroll down to height {new_height}")

        print("INFO  - Page seems to be fully loaded")

    @retry()
    def close_browser(self):
        try:
            self.browser.close()
            print("INFO  - Closed browser window")
            return True
        except Exception as e:
            print("ERROR - Error closing browser: ", e)
            raise Exception


def test_custom_requests():
    url_to_scrape = "https://www.scrapethissite.com/pages/simple/"

    try:
        scraper = CustomRequests()
        scraper.test_proxies()
        soup = scraper.fetch_soup(url_to_scrape)
        print(f"INFO  - Success fetching response from '{url_to_scrape}'")
    except Exception as e:
        print("ERROR - Unable to fetch response: ", e)

    if soup:
        try:
            scraper.save_soup_as_html(soup, "soup_test.html")
        except Exception as e:
            print("ERROR - Unable to save HTML content: ", e)


def test_custom_webdriver():
    url_to_scrape = "https://browsersize.com/"

    try:
        scraper = CustomWebDriver()
        scraper.test_proxies()
        scraper.open_browser()
        scraper.navigate(url_to_scrape)
        scraper.browser.save_screenshot('./screenshot.png')
        print("(INFO  - Saved screenshot image at './screenshot.png'")
        scraper.close_browser()
    except Exception as e:
        print("ERROR - ", e)


if __name__ == "__main__":

    test_custom_requests()
    test_custom_webdriver()
