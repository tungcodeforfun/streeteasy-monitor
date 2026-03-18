import os
import random
import time
import requests
from patchright.sync_api import sync_playwright

from src.streeteasymonitor.search import Search
from src.streeteasymonitor.database import Database
from src.streeteasymonitor.messager import Messager
from src.streeteasymonitor.config import Config

# Persistent browser profile directory
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'browser_profile')


class Monitor:
    def __init__(self, **kwargs):
        self.config = Config()
        self.db = Database()

        # Keep requests session for messaging API calls
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())

        # Playwright for fetching pages
        self.playwright = None
        self.context = None
        self.page = None

        self.kwargs = kwargs

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=os.path.abspath(PROFILE_DIR),
            channel='chromium',
            headless=False,
            no_viewport=True,
            ignore_default_args=['--enable-automation'],
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--start-maximized',
            ],
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self._warmup()
        return self

    def _warmup(self):
        """Visit StreetEasy homepage first to establish cookies and session."""
        from src.streeteasymonitor.search import Search
        print('Warming up browser session...')
        self.page.goto('https://streeteasy.com/', wait_until='domcontentloaded', timeout=30000)
        time.sleep(random.uniform(2, 4))
        # Handle bot detection during warmup
        dummy = type('obj', (object,), {'page': self.page, 'db': None, 'kwargs': {}})()
        search = Search.__new__(Search)
        search.page = self.page
        if search._is_bot_check():
            print('  Bot check on homepage — solving...')
            search._wait_for_bot_check()
            time.sleep(random.uniform(1, 2))

    def __exit__(self, *args, **kwargs):
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        if self.playwright:
            self.playwright.stop()
        self.session.close()

    def run(self):
        self.search = Search(self)
        self.listings = self.search.fetch()
        self.messager = Messager(self, self.listings)
        self.messager.send_messages()
