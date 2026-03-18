import json
import random
import re
import time

from bs4 import BeautifulSoup

from .config import Config
from .utils import build_url, get_datetime, get_area_map


class Search:
    """A search based on the current session, database instance, and keyword arguments for constructing a StreetEasy search URL.

    Attributes:
        area_map (dict[str, str]): A mapping of StreetEasy's neighborhood names and corresponding codes used for URL construction.
    """

    area_map: dict[str, str] = get_area_map()

    def __init__(self, monitor) -> None:
        """Initializes the search.

        Args:
            monitor (Monitor): A Monitor instance encapsulating a session, a database connection, and keyword arguments for constructing a search URL.

        Attributes:
            page (SeleniumPageWrapper): The page wrapper instance for fetching.
            db (Database): The database instance.
            kwargs (dict[str, str]): The search parameter components.
            codes (list[str, str]): The StreetEasy neighborhood codes corresponding to selected neighborhood names.

            price (str): The price range component of the search URL.
            area (str): The neighborhood code component of the search URL.
            beds (str): The number of beds component of the search URL.

            parameters (dict[str, str]): Dictionary mapping query components for URL construction.
            url (str): Search URL for the current query.
            listings (list[dict[str, str]]): Listings corresponding to the current search - initially empty.
        """

        self.page = monitor.page
        self.db = monitor.db
        self.kwargs = monitor.kwargs

        self.codes = [Search.area_map[area] for area in self.kwargs['areas']]

        self.area = ','.join(self.codes)
        self.price = f"{self.kwargs['min_price']}-{self.kwargs['max_price']}"
        self.beds = f"{self.kwargs['min_beds']}-{self.kwargs['max_beds']}"
        self.baths = f">={self.kwargs['baths']}"
        self.amenities = f"{','.join(self.kwargs['amenities'])}"
        self.no_fee = f"{1 if self.kwargs['no_fee'] == True else ''}"


        self.parameters = {
            'status': 'open',
            'price': self.price,
            'area': self.area,
            'beds': self.beds,
            'baths': self.baths,
            'amenities': self.amenities,
            'no_fee': self.no_fee,
        }

        self.url = build_url(**self.parameters)
        self.listings = []

    def _is_bot_check(self) -> bool:
        """Check if the current page is a bot detection challenge."""
        title = self.page.title().lower()
        content = self.page.content().lower()
        return (
            'captcha' in content
            or 'press & hold' in content
            or 'verify you are human' in content
            or 'just a moment' in title
            or 'attention required' in title
        )

    def _try_solve_press_and_hold(self) -> bool:
        """Attempt to solve a press-and-hold CAPTCHA automatically."""
        try:
            # Find the Cloudflare Turnstile iframe
            turnstile_frame = None
            for frame in self.page.frames:
                if 'challenges.cloudflare.com' in frame.url:
                    turnstile_frame = frame
                    break

            if not turnstile_frame:
                # Try finding the iframe element and its content frame
                iframe_el = self.page.query_selector('iframe[src*="challenges.cloudflare.com"], iframe[id*="turnstile"], iframe[title*="challenge"]')
                if iframe_el:
                    turnstile_frame = iframe_el.content_frame()

            if not turnstile_frame:
                print('  Could not find Turnstile iframe.')
                return False

            # Look for the interactive element inside the Turnstile iframe
            selectors = [
                'input[type="checkbox"]',
                '#challenge-stage',
                'div[id*="challenge"]',
                'button',
                'body',
            ]

            target = None
            for sel in selectors:
                el = turnstile_frame.query_selector(sel)
                if el and el.is_visible():
                    target = el
                    break

            if not target:
                print('  Could not find challenge element inside Turnstile.')
                return False

            box = target.bounding_box()
            if not box:
                return False

            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2

            # Human-like approach: move from a random starting point
            self.page.mouse.move(
                random.uniform(100, 400),
                random.uniform(100, 400)
            )
            time.sleep(random.uniform(0.5, 1.0))

            # Move toward the target with slight overshoot
            self.page.mouse.move(x + random.uniform(-5, 5), y + random.uniform(-5, 5))
            time.sleep(random.uniform(0.2, 0.5))

            # Press and hold
            print('  Pressing and holding challenge button...')
            self.page.mouse.down()
            time.sleep(random.uniform(7, 12))
            self.page.mouse.up()
            time.sleep(3)
            return True

        except Exception as e:
            print(f'  Auto-solve error: {e}')
        return False

    def _wait_for_bot_check(self, timeout=90) -> bool:
        """If a bot check is present, try to solve it automatically, then fall back to manual.
        Returns True if page is ready."""
        if not self._is_bot_check():
            return True

        print('  Bot check detected — attempting automatic solve...')

        # Try automated press-and-hold up to 3 times
        for attempt in range(3):
            self._try_solve_press_and_hold()
            time.sleep(3)
            if not self._is_bot_check():
                print('  Bot check passed automatically!')
                time.sleep(2)
                return True
            print(f'  Auto-solve attempt {attempt + 1} failed.')

        # Fall back to manual solving
        print('  Please solve the challenge manually in the browser window.')
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(3)
            if not self._is_bot_check():
                print('  Bot check passed!')
                time.sleep(2)
                return True

        print(f'  Bot check not resolved within {timeout}s.')
        return False

    def _capture_rental_ids(self, response):
        """Intercept GraphQL API responses to extract rental IDs and listing details."""
        if 'api-v6.streeteasy.com' not in response.url:
            return
        try:
            body = response.json()
            edges = body.get('data', {}).get('searchRentals', {}).get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                rental_id = node.get('id')
                url_path = node.get('urlPath', '')
                if rental_id and url_path:
                    full_url = f'https://streeteasy.com{url_path}'
                    self._rental_id_map[full_url] = rental_id
                    self._listing_details[full_url] = {
                        'beds': node.get('bedroomCount'),
                        'baths': (node.get('fullBathroomCount', 0) or 0) + (node.get('halfBathroomCount', 0) or 0) * 0.5,
                        'status': (node.get('status') or '').capitalize(),
                        'building_type': (node.get('buildingType') or '').replace('_', ' ').capitalize(),
                        'source': node.get('sourceGroupLabel', ''),
                    }
        except Exception:
            pass

    def fetch(self) -> list[dict[str, str]]:
        """Check the search URL for new listings, paginating through all results."""

        print(f'Running script with parameters:\n{json.dumps(self.parameters, indent=2)}\n')
        print(f'Base URL: {self.url}')

        all_listings = []
        page_num = 1
        seen_ids = set()  # Track listing IDs to detect when we've seen all listings
        self._rental_id_map = {}  # URL -> numeric rental ID from API
        self._listing_details = {}  # URL -> {beds, baths, status, ...} from API

        # Listen for API responses to capture rental IDs
        self.page.on('response', self._capture_rental_ids)

        try:
            while True:
                # StreetEasy uses &page=N for pagination
                page_url = f"{self.url}&page={page_num}" if page_num > 1 else self.url
                print(f'\n--- Page {page_num} ---')
                print(f'URL: {page_url}')

                self.page.goto(page_url, wait_until='domcontentloaded', timeout=60000)

                # Check for bot detection
                if not self._wait_for_bot_check():
                    print('Stopping due to bot detection.')
                    break

                # Wait for listing cards to appear
                try:
                    self.page.wait_for_selector('[data-testid="listing-card"]', timeout=15000)
                except Exception:
                    print(f'No listings found on page {page_num}, stopping pagination.')
                    break

                content = self.page.content()
                parser = Parser(content.encode(), self.db, self.page, self.kwargs, self._rental_id_map, self._listing_details)

                # Parse all cards (before filtering) to check for pagination end
                all_cards = parser.soup.select('[data-testid="listing-card"]')
                parsed_all = [parser.parse(card) for card in all_cards]
                new_card_ids = [p['listing_id'] for p in parsed_all if p['listing_id'] not in seen_ids]
                seen_ids.update(p['listing_id'] for p in parsed_all)

                # Get filtered listings for messaging
                page_listings = [card for card in parsed_all if parser.filter(card)]

                print(f'Found {len(page_listings)} new listings on page {page_num}')

                if not new_card_ids:
                    print(f'No new unique cards on page {page_num}, stopping pagination.')
                    break

                all_listings.extend(page_listings)

                # Randomized delay between pages to appear more human
                delay = random.uniform(3, 7)
                print(f'  Waiting {delay:.1f}s before next page...')
                time.sleep(delay)
                page_num += 1

        except Exception as e:
            print(f'{get_datetime()} Error fetching page: {e}\n')
            import traceback
            traceback.print_exc()

        # Stop listening for API responses
        self.page.remove_listener('response', self._capture_rental_ids)

        self.listings = all_listings

        if not self.listings:
            print(f'{get_datetime()} No new listings.\n')
        else:
            print(f'\nTotal: {len(self.listings)} listings across {page_num} page(s)')

        return self.listings


class Parser:
    """Separates parsing functionality from search.

    Attributes:
        price_pattern (re.Pattern): Regular expression used for stripping commas and dollar signs from listing price.
    """

    price_pattern = re.compile(r'[$,]')

    def __init__(self, content: bytes, db, page=None, kwargs=None, rental_id_map=None, listing_details=None) -> None:
        """Initialize the parse object.

        Args:
            content (bytes): HTML content of a successful GET request to the search URL.
            db (Database): Database instance used for fetching listing IDs that already exist in the database.
            page: Page wrapper instance for fetching listing details.
            kwargs: Search parameters from the form (min_price, max_price, areas, etc.)
            rental_id_map: URL -> numeric rental ID mapping from intercepted API responses.
            listing_details: URL -> {beds, baths, status, ...} from intercepted API responses.

        Attributes:
            soup (bs4.BeautifulSoup): Beautiful Soup object for parsing HTML contents.
            existing_ids (list[str]): Listing IDs that have already been stored in the database.
        """

        self.soup = BeautifulSoup(content, 'html.parser')
        self.existing_ids = db.get_existing_ids()
        self.page = page
        self.kwargs = kwargs or {}
        self.rental_id_map = rental_id_map or {}
        self.listing_details = listing_details or {}
        self._description_cache = {}

    def parse(self, card) -> dict[str, str]:
        """Parse the contents of one listing."""
        # Find URL and address from the listing link
        link = card.select_one('a[href*="streeteasy.com/building"]')
        url = link['href'] if link else ''
        address = link.text.strip() if link else ''

        # Get numeric rental ID from intercepted API response
        listing_id = self.rental_id_map.get(url, '')
        if not listing_id and url:
            # Fallback: extract slug from URL
            match = re.search(r'/building/[^/]+/([^?]+)', url)
            if match:
                listing_id = match.group(1)

        # Find price - look for element with PriceInfo in class
        price_elem = card.select_one('[class*="PriceInfo"]')
        price = ''
        if price_elem:
            price_text = price_elem.get_text()
            # Extract first price (e.g., "$3,600" from "$3,600base rent...")
            price_match = re.search(r'\$[\d,]+', price_text)
            if price_match:
                price = Parser.price_pattern.sub('', price_match.group())

        # Find neighborhood from title (e.g., "Rental unit in Bushwick")
        title_elem = card.select_one('[class*="ListingDescription-module__title"]')
        neighborhood = ''
        if title_elem:
            title_text = title_elem.text.strip()
            if ' in ' in title_text:
                neighborhood = title_text.split(' in ')[-1].strip()

        # Get extra details from API response
        details = self.listing_details.get(url, {})

        return {
            'listing_id': listing_id,
            'url': url,
            'price': price,
            'address': address,
            'neighborhood': neighborhood,
            'beds': details.get('beds', ''),
            'baths': details.get('baths', ''),
            'building_type': details.get('building_type', ''),
            'source': details.get('source', ''),
        }

    # Pattern to extract street number from address (e.g., "123 East 45th Street" -> 45)
    street_pattern = re.compile(r'(?:East|West|E|W)?\s*(\d+)(?:st|nd|rd|th)?\s*(?:Street|St)', re.IGNORECASE)

    def get_description(self, url: str) -> str:
        """Fetch the description from a listing's detail page."""
        if not self.page or not url:
            return ''

        if url in self._description_cache:
            return self._description_cache[url]

        try:
            # Random delay before fetching each listing detail
            time.sleep(random.uniform(1.5, 3))
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            # Wait for description to load
            self.page.wait_for_selector('[data-testid="listing-details-description"], [class*="Description"]', timeout=10000)
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Try multiple selectors for description
            desc_elem = soup.select_one('[data-testid="listing-details-description"]')
            if not desc_elem:
                desc_elem = soup.select_one('[class*="Description"]')
            if not desc_elem:
                desc_elem = soup.select_one('.listing-description')

            description = desc_elem.get_text(separator=' ', strip=True) if desc_elem else ''
            self._description_cache[url] = description
            return description
        except Exception:
            self._description_cache[url] = ''
            return ''

    def filter(self, target) -> bool:
        """Filter a listing based on attributes not captured by StreetEasy's interface natively."""
        if target['listing_id'] in self.existing_ids:
            print(f"  FILTERED: {target['address']} - already in database")
            return False

        for key, substrings in Config.filters.items():
            target_value = target.get(key, '')
            if any(substring in target_value for substring in substrings):
                print(f"  FILTERED: {target['address']} - {key} contains blocked substring")
                return False

        # Note: We search with status:open so inactive listings shouldn't appear
        # If a status field is present and not active, filter it out
        status = target.get('status', '')
        if status and status.lower() not in ('', 'active', 'open'):
            return False

        # Filter out listings outside price range (use search kwargs, fall back to Config.defaults)
        min_price = self.kwargs.get('min_price') or Config.defaults.get('min_price', 0)
        max_price = self.kwargs.get('max_price') or Config.defaults.get('max_price', float('inf'))
        try:
            price = int(target.get('price', 0))
            if price < min_price or price > max_price:
                print(f"  FILTERED: {target['address']} - price ${price} outside range ${min_price}-${max_price}")
                return False
        except (ValueError, TypeError):
            pass

        # Filter out listings not in configured neighborhoods (use search kwargs, fall back to Config.defaults)
        configured_areas = self.kwargs.get('areas') or Config.defaults.get('areas', [])
        if configured_areas:
            neighborhood = target.get('neighborhood', '')
            # Check if neighborhood matches any configured area (case-insensitive partial match)
            if not any(area.lower() in neighborhood.lower() or neighborhood.lower() in area.lower()
                       for area in configured_areas):
                print(f"  FILTERED: {target['address']} - neighborhood '{neighborhood}' not in configured areas")
                return False

        # Filter out addresses above max street number
        max_street = getattr(Config, 'max_street_number', None)
        if max_street:
            address = target.get('address', '')
            match = Parser.street_pattern.search(address)
            if match:
                street_num = int(match.group(1))
                print(f"  DEBUG: Address '{address}' -> street {street_num}, max {max_street}")
                if street_num > max_street:
                    print(f"  FILTERED: {address} - street number {street_num} > {max_street}")
                    return False
        else:
            print(f"  DEBUG: max_street not set")

        # Filter out listings with restricted housing keywords in description
        description_filters = getattr(Config, 'description_filters', [])
        if description_filters and self.page:
            url = target.get('url', '')
            description = self.get_description(url).lower()
            if any(keyword.lower() in description for keyword in description_filters):
                return False

        return True

    @property
    def listings(self) -> dict[str, str]:
        """Return all parsed and filtered listings."""
        cards = self.soup.select('[data-testid="listing-card"]')
        print(f'DEBUG: Found {len(cards)} listing cards on page')
        parsed = [self.parse(card) for card in cards]
        print(f'DEBUG: Parsed {len(parsed)} listings')
        if parsed:
            print(f'DEBUG: First parsed listing: {parsed[0]}')
        filtered = [card for card in parsed if self.filter(card)]
        print(f'DEBUG: After filtering: {len(filtered)} listings remain')
        return filtered
