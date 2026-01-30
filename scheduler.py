"""
Cross-platform scheduler for StreetEasy Monitor.
Works on macOS, Windows, and Linux.

Usage:
    python scheduler.py              # Run every 8 minutes (default)
    python scheduler.py --interval 5 # Run every 5 minutes
    python scheduler.py --once       # Run once and exit
"""

import argparse
import time
import sys
from datetime import datetime

from main import main
from src.streeteasymonitor.config import Config


def run_monitor():
    """Run the monitor and handle any errors."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n{"="*60}')
    print(f'[{timestamp}] Starting monitor run...')
    print(f'{"="*60}\n')

    try:
        main(**Config.defaults)
        print(f'\n[{timestamp}] Monitor run completed successfully.')
    except Exception as e:
        print(f'\n[{timestamp}] Error during monitor run: {e}')


def scheduler(interval_minutes: int):
    """Run the monitor on a schedule."""
    print(f'StreetEasy Monitor Scheduler')
    print(f'Running every {interval_minutes} minutes. Press Ctrl+C to stop.\n')

    # Run immediately on start
    run_monitor()

    while True:
        try:
            # Sleep for the interval
            time.sleep(interval_minutes * 60)
            run_monitor()
        except KeyboardInterrupt:
            print('\n\nScheduler stopped by user.')
            sys.exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='StreetEasy Monitor Scheduler')
    parser.add_argument('--interval', type=int, default=8,
                        help='Minutes between runs (default: 8)')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit')

    args = parser.parse_args()

    if args.once:
        run_monitor()
    else:
        scheduler(args.interval)
