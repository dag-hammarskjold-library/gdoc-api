"""
Runs gdoc-dlx for one day for a selected duty station. Completed days are 
recorded in the database. Each subsequent run increments the day, so it can be 
run over time.

Usage:
    from gdoc_api.scripts import gdoc_dlx_retro
    
    gdoc_dlx_retro.run()
"""

import sys
import boto3
from argparse import ArgumentParser
from datetime import datetime, timedelta
from pymongo import DESCENDING
from dlx import DB
from gdoc_api.scripts import gdoc_dlx

def get_args(**kwargs):
    parser = ArgumentParser(prog='gdoc_dlx_retro', description='Run gdoc-dlx for one day for a selected duty station; the date comes from the database.')
    parser.add_argument('--station', type=str, default=None, help='Duty station (NY or GE)')

    if kwargs:
        process_kwargs(**kwargs)
    
    return parser.parse_args()

def process_kwargs(**kwargs):
    """If being imported as a function, process kwargs into command line args 
    so they can be parsed by argparse"""

    sys.argv = [sys.argv[0]]
    params = ('station')

    for param in ('station'):
        if param not in params:
            raise Exception(f'Required param {param}')

    for param, arg in kwargs.items():
        if param not in params:
            raise Exception(f'Invalid argument: "{param}"')
        else:
            sys.argv.append(f'--{param}={arg}')

def run():
    args = get_args()
    station = args.station
    
    ssm = boto3.client('ssm')
    DB.connect(ssm.get_parameter(Name='prodISSU-admin-connect-string')['Parameter']['Value'], database='undlFiles')
    col = DB.handle['gdoc_dlx_retro']

    # Get the most recent date that has been processed, and increment it by one day to get the next date to process.
    # If there is no record in the database, start with the first known gdoc day (2017-07-24).
    last_record = col.find_one({'station': station}, sort=[('issue_date', DESCENDING)])
        
    if not last_record:
        next_date = datetime.strptime('2017-07-24', '%Y-%m-%d') # first known gdoc day
    else:    
        next_date = last_record['issue_date'] + timedelta(days=1)

    print(f"Running gdoc-dlx for {station} for {next_date.strftime('%Y-%m-%d')}")
    gdoc_dlx.run(station=station, date=next_date.strftime('%Y-%m-%d'), recursive=True)

    print(f"Recording {next_date.strftime('%Y-%m-%d')} as completed for {station} in the database")    
    col.insert_one({'issue_date': next_date, 'station': station, 'completed': datetime.now()})

if __name__ == '__main__':
    run()
