# StreetEasy Monitor

## Overview
Python script that monitors StreetEasy for new rental listings and automatically sends inquiry messages. Includes a Flask web interface for viewing contacted listings and running searches.

## Tech Stack
- **Python 3.12** with pyenv
- **Playwright** with stealth mode for browser automation (bypasses bot detection)
- **BeautifulSoup4** for HTML parsing
- **Flask** + Flask-WTF + HTMX + Bootstrap for web UI
- **SQLite** for tracking contacted listings

## Project Structure
```
├── main.py                    # CLI entry point
├── app/
│   ├── app.py                 # Flask app (port 8002)
│   └── forms.py               # WTForms definitions
├── src/streeteasymonitor/
│   ├── config.py              # Search defaults, filters, env vars
│   ├── monitor.py             # Main scraping logic
│   ├── search.py              # URL construction, search params
│   ├── messager.py            # Auto-messaging via Playwright
│   ├── database.py            # SQLite operations
│   └── utils.py               # Helpers
└── cron/                      # Scheduling scripts
```

## Configuration

### Environment Variables (.env)
Required for messaging:
```
MESSAGE='...'
PHONE='...'
EMAIL='...'
NAME='...'
```

### Search Defaults (src/streeteasymonitor/config.py)
- `defaults` dict: price range, beds, baths, neighborhoods, amenities
- `dry_run`: True = preview only, False = send messages
- `export_csv`: export listings to data/ folder
- `max_street_number`: filter addresses above this street number
- `description_filters`: keywords to exclude (senior housing, income-restricted, etc.)

## Running
```bash
# CLI (uses config.py defaults)
python main.py

# Flask app
python -m app.app
```

## Important Constraints
- Requires visible browser window (no headless) to avoid bot detection
- StreetEasy sends confirmation emails for every inquiry
- Respect StreetEasy ToS and rate limits
- Uses Paddaddy integration for additional rental info

## Development Notes
- Playwright browser must be installed: `playwright install chromium`
- Bot detection is aggressive - stealth mode and visible browser are necessary
- Database stores contacted listing IDs to avoid duplicate messages
