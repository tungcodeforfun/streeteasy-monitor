from environs import Env
from fake_useragent import UserAgent


class Config:
    defaults = {
        'min_price': 0,
        'max_price': 2500,
        'min_beds': 0,
        'max_beds': 1,
        'baths': 1,
        'areas': [
            # Manhattan below 70th Street
            'Midtown',
            'Midtown East',
            'Midtown West',
            'Midtown South',
            'Chelsea',
            'West Chelsea',
            'Gramercy Park',
            'Flatiron',
            'NoMad',
            'Kips Bay',
            'Murray Hill',
            'Turtle Bay',
            'Sutton Place',
            'Beekman',
            'East Village',
            'West Village',
            'Greenwich Village',
            'Nolita',
            'Little Italy',
            'Chinatown',
            'Two Bridges',
            'Lower East Side',
            'Tribeca',
            'Financial District',
            'Battery Park City',
            'Hudson Yards',
            'Hudson Square',
            "Hell's Kitchen",
            'Stuyvesant Town/PCV',
        ],
        'amenities': [
            # 'pets',
            # 'doorman',
            # 'laundry',
            # 'elevator',
            # 'private_outdoor_space',
            # 'dishwasher',
            # 'washer_dryer',
            # 'gym',
        ],
        'no_fee': False,
    }

    # Max street number allowed (filter out addresses above this)
    max_street_number = 70

    # Set to True to preview listings without sending messages
    dry_run = True

    # Set to True to export listings to CSV file in data/ folder
    export_csv = True

    filters = {
        'url': [
            '?featured=1',
            '?infeed=1',
        ],
        'address': [],
        'neighborhood': [
            'New Development',
        ],
    }

    # Keywords to filter out from listing descriptions (case-insensitive)
    description_filters = [
        'senior housing',
        'income restricted',
        'income-restricted',
        'income requirement',
        'minimum income',
        'maximum income',
        '62 years or older',
        '55 and older',
        'age restricted',
        'age-restricted',
        'lottery',
        'affordable housing',
        'section 8',
        'hpd',
        'mitchell-lama',
        'hdfc',
    ]

    def __init__(self):
        self.env = Env()
        self.env.read_env()

    def get_headers(self):
        self.ua = UserAgent()
        self.random_user_agent = self.ua.random
        self.default_user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        self.user_agent = self.random_user_agent or self.default_user_agent

        return {
            'user-agent': self.user_agent,
            'accept-language': 'en-US,en;q=0.9',
            'referer': 'https://streeteasy.com/',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://streeteasy.com',
        }

    def get_field_values(self):
        return {
            'message': self.env('MESSAGE', default=''),
            'phone': self.env('PHONE', default=''),
            'email': self.env('EMAIL', default=''),
            'name': self.env('NAME', default=''),
            'search_partners': None,
        }
