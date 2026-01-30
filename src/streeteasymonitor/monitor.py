import requests
import undetected_chromedriver as uc

from src.streeteasymonitor.search import Search
from src.streeteasymonitor.database import Database
from src.streeteasymonitor.messager import Messager
from src.streeteasymonitor.config import Config


class SeleniumPageWrapper:
    """Wrapper to make Selenium driver work with existing code expecting Playwright-like interface."""
    def __init__(self, driver):
        self.driver = driver
        self._mouse = MouseWrapper(driver)

    def goto(self, url, wait_until=None, timeout=None):
        self.driver.get(url)

    def content(self):
        return self.driver.page_source

    def wait_for_selector(self, selector, timeout=15000):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        # Convert CSS selector to work with Selenium
        wait = WebDriverWait(self.driver, timeout / 1000)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

    @property
    def mouse(self):
        return self._mouse

    def close(self):
        pass  # Driver closed separately


class MouseWrapper:
    def __init__(self, driver):
        self.driver = driver

    def move(self, x, y):
        from selenium.webdriver.common.action_chains import ActionChains
        action = ActionChains(self.driver)
        action.move_by_offset(x, y).perform()
        action.reset_actions()


class Monitor:
    def __init__(self, **kwargs):
        self.config = Config()
        self.db = Database()

        # Keep requests session for messaging API calls
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())

        self.driver = None
        self.page = None

        self.kwargs = kwargs

    def __enter__(self):
        import os
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1280,800')
        # Use persistent profile
        user_data_dir = os.path.expanduser('~/.streeteasy-chrome')
        options.add_argument(f'--user-data-dir={user_data_dir}')

        self.driver = uc.Chrome(options=options, use_subprocess=True)
        self.page = SeleniumPageWrapper(self.driver)
        return self

    def __exit__(self, *args, **kwargs):
        if self.driver:
            self.driver.quit()
        self.session.close()

    def run(self):
        self.search = Search(self)
        self.listings = self.search.fetch()
        self.messager = Messager(self, self.listings)
        self.messager.send_messages()
