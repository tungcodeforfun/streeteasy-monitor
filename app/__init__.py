from datetime import datetime, timedelta, UTC

from dateutil.tz import gettz
from flask_bootstrap import Bootstrap5
from flask import Flask, flash, request, redirect, render_template, session, url_for
import requests
import timeago

from src.streeteasymonitor.database import Database
from src.streeteasymonitor.config import Config

from .forms import SearchForm

from main import main


def create_app():
    paddaddy_base_url = 'https://paddaddy.app'
    offermate_lookup_api = 'https://offermate.app/unit_lookup'

    app = Flask(__name__)
    bootstrap = Bootstrap5(app)
    db = Database()

    class FlaskConfig:
        SECRET_KEY = 'dev'

    app.config.from_object(FlaskConfig())

    @app.template_filter()
    def usd(value):
        """Format value as USD."""
        return f'${int(value):,}'

    @app.template_filter()
    def format_datetime(created_at):
        """Format date and time for current timezone."""
        local_tz = gettz()
        now = datetime.now(local_tz)
        parsed = datetime.fromisoformat(created_at).replace(tzinfo=UTC).astimezone()

        time_ago = timeago.format(parsed, now)

        date_formatted = parsed.strftime('%B %e, %Y')
        time_formatted = parsed.strftime('%l:%M %p')
        datetime_formatted = f'{date_formatted} {time_formatted}'

        return time_ago if now - parsed < timedelta(hours=8) else datetime_formatted
    
    @app.route('/', methods=['GET', 'POST'])
    def index():
        form = SearchForm()

        if request.method == 'POST':
            print(f'POST received, form data: {request.form}', flush=True)
            print(f'Form validates: {form.validate_on_submit()}', flush=True)
            if form.errors:
                print(f'Form errors: {form.errors}', flush=True)
            if form.validate_on_submit():
                # Extract form data (use 'is not None' to preserve False, 0, and [] values)
                kwargs = {
                    field.name: field.data if field.data is not None else field.default
                    for field in form
                    if field.name not in ('csrf_token', 'submit', 'dry_run', 'max_street')
                }

                # Set config options from form
                Config.dry_run = form.dry_run.data
                if form.max_street.data:
                    Config.max_street_number = form.max_street.data
                else:
                    Config.max_street_number = None

                print(f'Running search with: {kwargs}')
                found_listings = main(**kwargs)
                print(f'Found {len(found_listings) if found_listings else 0} listings')

                # Show found listings if dry run, otherwise show from database
                if Config.dry_run and found_listings:
                    # Add placeholder created_at for display
                    from datetime import datetime
                    for listing in found_listings:
                        listing['created_at'] = datetime.now().isoformat()
                    print(f'Returning {len(found_listings)} listings for dry run')
                    return render_template('table.html', listings=found_listings)
                else:
                    db_listings = db.get_listings_sorted()
                    print(f'Returning {len(db_listings)} listings from database')
                    return render_template('table.html', listings=db_listings)

            print('Invalid form submission\n')
            return redirect(url_for('index'))

        return render_template(
            'index.html',
            listings=db.get_listings_sorted(),
            form=SearchForm(),  # Use defaults from Config
        )
    

    @app.route('/<path:url>', methods=['GET'])
    def url(url):
        try:
            params = {'q': url}
            r = requests.get(offermate_lookup_api, params=params)
            json = r.json()
            if (
                json.get('matching_listings')
                and json['matching_listings'][0]['similarity_type'] == 'exact_match'
            ):
                paddaddy_id = json['matching_listings'][0]['url']
                redirect_url = paddaddy_base_url + paddaddy_id
            else:
                redirect_url = url
        except Exception as e:
            print(f'Error: {e}')
            redirect_url = url

        return redirect(redirect_url, code=302)

    return app
