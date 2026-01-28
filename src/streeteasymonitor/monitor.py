import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from src.streeteasymonitor.search import Search
from src.streeteasymonitor.database import Database
from src.streeteasymonitor.messager import Messager
from src.streeteasymonitor.config import Config


class Monitor:
    def __init__(self, **kwargs):
        self.config = Config()
        self.db = Database()

        # Keep requests session for messaging API calls
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())

        # Playwright for fetching pages
        self.playwright = None
        self.browser = None
        self.page = None
        self.stealth = Stealth()

        self.kwargs = kwargs

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--start-maximized',
            ]
        )
        self.page = self.browser.new_page()
        self.stealth.apply_stealth_sync(self.page)
        return self

    def __exit__(self, *args, **kwargs):
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.session.close()

    def run(self):
        self.search = Search(self)
        self.listings = self.search.fetch()
        self.messager = Messager(self, self.listings)
        self.messager.send_messages()
