"""
Runs gdoc-dlx for every day since the first known date of the gDoc feed.
Completed days are recorded in the database and the script automatically
starts from the last completed day. Logs are printed to STDOUT for capture 
in CloudWatch

Usage:
    from gdoc_api.scripts import gdoc_dlx_retro
    
    gdoc_dlx_retro.run()
"""

import boto3
from datetime import datetime, timedelta
from pymongo import DESCENDING
from dlx import DB
from gdoc_api.scripts import gdoc_dlx

def run():
    ssm = boto3.client('ssm')
    DB.connect(ssm.get_parameter(Name='connect-string')['Parameter']['Value'])
    col = DB.handle['gdoc_dlx_retro']
    last_record = col.find_one({}, sort=[('issue_date', DESCENDING)])
        
    if not last_record:
        next_date = datetime.strptime('2017-07-24', '%Y-%m-%d') # first known gdoc day
    else:    
        next_date = last_record['issue_date'] + timedelta(days=1)
    
    for station in ('NY', 'GE'):
        gdoc_dlx.run(station=station, date=next_date.strftime('%Y-%m-%d'))
        
    col.insert_one({'issue_date': next_date, 'completed': datetime.now()})

###

if __name__ == '__main__':
    run()
