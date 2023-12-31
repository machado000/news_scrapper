'''
This class is used to scrap web pages by fetching content using proxies and random user agents for anonymity.
It uses package `requests` to provide methods for retrieving responses with `.get_response` or
get HTML soup object with `.fetch_soup`.
It also use package `selenium` to initialize a webdriver and provide methods `.open_driver`, `.navigate` to url
and `.fecht_element` for further processing.
v.2023-09-05
'''
import os
import time
import zipfile
import requests

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fake_useragent import UserAgent
from requests.exceptions import HTTPError
from selenium.webdriver import Chrome, ChromeOptions
# from selenium.webdriver import Edge, EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src._decorators import retry


class CustomRequests:

    def __init__(self, username, password, endpoint, port):

        # proxy_auth = HTTPProxyAuth(username, password)
        proxy_url = f'http://{username}:{password}@{endpoint}:{port}'

        self.session = requests.Session()
        self.session.proxies = {'http': proxy_url, 'https': proxy_url}
        # self.session.auth = proxy_auth

        ua = UserAgent(
            browsers=['edge', 'chrome', 'firefox'],
            fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0'
        )

        self.session.headers.update({'User-Agent': ua.random})
        soup = self.fetch_soup('https://ipinfo.io/ip')
        print(f"INFO  - Success opening 'requests' session with proxy ip '{soup.text}'")

    @retry()
    def get_response(self, url, **kwargs):
        try:
            response = self.session.get(url, timeout=5, **kwargs)
            return response

        except HTTPError as e:
            if e.response.status_code == 403 or e.response.status_code == 429:
                print("INFO - 'Too Many Requests' error. Retrying...")
                raise  # This will trigger the retry mechanism

        except Exception as e:
            print('INFO  - Failed to get response: ', e)
            raise Exception(f'HTTP Error: {e}')

    def fetch_soup(self, url):
        try:
            response = self.get_response(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        except Exception as e:
            print('INFO  - Failed to fetch soup: ', e)
            raise Exception

    def fetch_soup_lxml(self, url):
        try:
            response = self.get_response(url)
            soup = BeautifulSoup(response.text, features='xml')
            return soup
        except Exception as e:
            print('INFO  - Failed to fetch soup: ', e)
            raise Exception

    def save_soup_as_html(self, soup, filename):
        try:
            if soup:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(soup.prettify())
                print(f"INFO  - HTML content saved as '{filename}'")
                return True
        except Exception as e:
            print('ERROR - Unable to save HTML content: ', e)
            raise Exception

    @retry()
    def get_redirected_url(self, url):
        cookies = {'CONSENT': 'YES+cb.20220419-08-p0.cs+FX+111'}

        try:
            response = self.session.get(url, cookies=cookies)
            # response.raise_for_status()
            # final_url = response.url
            soup = BeautifulSoup(response.text, 'html.parser')
            final_url = soup.a['href']
            return final_url

        except HTTPError as e:
            if e.response.status_code == 403 or e.response.status_code == 429:
                print("INFO - 'Too Many Requests' error. Retrying...")
                raise  # This will trigger the retry mechanism

        except Exception as e:
            print("INFO  - Failed to get response: ", e)
            raise Exception(f'HTTP Error: {e}')


class CustomWebDriver:

    def __init__(self, username=None, password=None, endpoint=None, port=None):

        self.options = ChromeOptions()
        self.options.use_chromium = True  # Use Chromium-based Edge
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--disable-infobars')
        self.options.add_argument('--enable-automation')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument('--ignore-ssl-errors')
        self.options.add_argument('--window-size=1920,1020')
        # self.options.add_argument('--headless=new')
        # self.options.add_argument('--disable-gpu')
        # self.options.add_argument('--disable-javascript')  # EXPERIMENTAL
        # self.options.add_argument('--incognito')
        user_data_dir = 'C:/Users/joaom/Projetos/13dnews/webdriver_data'

        self.options.add_argument(f'--user-data-dir={user_data_dir}')

        self.options.add_experimental_option('detach', True)  # DEBUG
        self.options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.options.add_experimental_option('useAutomationExtension', False)

        self.options.add_argument(
            f'--user-agent={"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"}')  # noqa
        # self.ua = UserAgent(browsers=['edge', 'chrome', 'firefox'], os=['windows', 'macos'], min_percentage=0.03)
        # self.options.add_argument(f'--user-agent={self.ua.random}')

        # self.proxies_extension = self.proxies(username, password, endpoint, port)
        # self.options.add_extension(self.proxies_extension)

        self.driver = None

    @retry()
    def open_driver(self):
        try:

            # # Try to connect to an existing session. If successful, return the existing driver
            # existing_driver = Chrome(command_executor='http://127.0.0.1:4444/wd/hub')
            # return existing_driver

            # except Exception as e:
            #     print('INFO  - Error connect to an existing webdriver: ', e)
            print('INFO  - Opening a new session')
            self.driver = Chrome(options=self.options)
            self.driver.implicitly_wait(0.5)
            self.driver.set_window_position(2560, 0)
            # self.driver.delete_all_cookies()
            # Change the property value of the  navigator  for webdriver to undefined
            # self.driver.execute_script('Object.defineProperty(navigator, 'webdriver', {get: () => undefined})')

            height = self.driver.get_window_size().get('height')
            width = self.driver.get_window_size().get('width')
            user_agent = self.driver.execute_script('return navigator.userAgent;')
            self.driver.get('https://ipinfo.io/ip')
            body_element = self.driver.find_element(By.TAG_NAME, 'body')
            external_ip = body_element.text

            print('INFO  - Opened an Edge driver window with settings:',
                  f'INFO  - UA: {user_agent}',
                  f'INFO  - Proxy IPv4: {external_ip}',
                  f'INFO  - Window size: {width}x{height}',
                  sep='\n')

            return self.driver

        except Exception as e:
            print('ERROR - Could not initialize driver: ', e)
            raise Exception

    @retry()
    def navigate(self, url):
        print(f'INFO  - Navigating to {url}')
        try:
            self.driver.get(url)
            print('INFO  - [Success]')
        except Exception as e:
            print(f'ERROR - Error navigating to {url}: ', e)
            raise Exception

    @retry()
    def fetch_element(self, css_selector):
        print(f'INFO  - Fetching elements with selector: {css_selector[0:41]}')
        try:
            # elements = WebDriverWait(self.driver, timeout).until(
            #     EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            # )
            elements = self.driver.find_elements(By.CSS_SELECTOR, value=css_selector)
            return elements
        except Exception as e:
            print(f'ERROR - Could not find element {css_selector}: ', e)

        return []

    @retry()
    def infinite_scroll(self, scroll_pause_time=10, end_scroll_attempts=3):
        last_height = self.driver.execute_script('return document.body.scrollHeight')
        # footer = self.driver.find_element(By.CSS_SELECTOR, 'div.footerstyles__Footer-sc-1ar2w9j-0.jdgzxt')
        # ActionChains(self.driver).scroll_to_element(footer).perform()
        print(f'INFO  - Window opened with content height of {last_height}')
        # self.driver.save_screenshot(f'./screenshot_{last_height}.png')  # DEBUG

        attempts = 0

        while attempts < end_scroll_attempts:

            for _ in range(3):
                # press PAGE_DOWN or SCROLL 3 times
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
                time.sleep(3)  # time between key presses / scrolls

            # ActionChains(self.driver).scroll_by_amount(0, 600).perform()
            time.sleep(scroll_pause_time)  # Wait for aditional content to load

            new_height = self.driver.execute_script('return document.body.scrollHeight')
            # self.driver.save_screenshot(f'./screenshot_{new_height}.png')  # DEBUG

            if new_height == last_height:
                attempts += 1
                print(f'INFO  - Could not load new content (retry {attempts}/{end_scroll_attempts})')
            else:
                attempts = 0  # Reset attempts if scroll height changes

            last_height = new_height
            print(f'INFO  - Scroll down to height {new_height}')

        print('INFO  - Page seems to be fully loaded')

    @retry()
    def close_driver(self):
        try:
            self.driver.close()
            print('INFO  - Closed driver window')
            return True
        except Exception as e:
            print('ERROR - Error closing driver: ', e)
            raise Exception

    def proxies(self, username, password, endpoint, port):
        manifest_json = '''
        {
            'version': '1.0.0',
            'manifest_version': 2,
            'name': 'Proxies',
            'permissions': [
                'proxy',
                'tabs',
                'unlimitedStorage',
                'storage',
                '<all_urls>',
                'webRequest',
                'webRequestBlocking'
            ],
            'background': {
                'scripts': ['background.js']
            },
            'minimum_chrome_version':'22.0.0'
        }
        '''

        background_js = '''
        var config = {
                mode: 'fixed_servers',
                rules: {
                singleProxy: {
                    scheme: 'http',
                    host: '%s',
                    port: parseInt(%s)
                },
                bypassList: ['localhost']
                }
            };

        chrome.proxy.settings.set({value: config, scope: 'regular'}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: '%s',
                    password: '%s'
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ['<all_urls>']},
                    ['blocking']
        );
        ''' % (endpoint, port, username, password)

        extension = 'proxies_extension.zip'

        with zipfile.ZipFile(extension, 'w') as zp:
            zp.writestr('manifest.json', manifest_json)
            zp.writestr('background.js', background_js)

        return extension


def test_custom_requests(username, password, endpoint, port):
    # url_to_scrape = 'https://www.scrapethissite.com/pages/simple/'

    try:
        scraper = CustomRequests(username, password, endpoint, port)
        print(type(scraper.session))
        # scraper.test_proxies()

    except Exception as e:
        print('ERROR - Unable to fetch response: ', e)


def test_custom_webdriver(username, password, endpoint, port):
    url_to_scrape = 'https://browsersize.com/'

    try:
        scraper = CustomWebDriver(username, password, endpoint, port)
        # scraper.test_proxies()
        scraper.open_driver()
        scraper.navigate(url_to_scrape)
        scraper.driver.save_screenshot('./files/screenshot.png')
        print("INFO  - Saved screenshot image at './files/screenshot.png'")
        scraper.close_driver()
    except Exception as e:
        print('ERROR - ', e)


if __name__ == '__main__':

    load_dotenv()
    username = os.getenv('PROXY_USERNAME')
    password = os.getenv('PROXY_PASSWORD')
    endpoint = os.getenv('PROXY_SERVER')
    port = os.getenv('PROXY_PORT')
    # proxy_string = f'http://{username}:{password}@{endpoint}:{port}'
    # print(proxy_string)

    test_custom_requests(username, password, endpoint, port)

    test_custom_webdriver(username, password, endpoint, port)
