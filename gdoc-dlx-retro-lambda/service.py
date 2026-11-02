# AWS Lambda function that runs gdoc_dlx 

from gdoc_api.scripts import gdoc_dlx
import sys, datetime

def handler(event, context):
    print(f"Processing {event}")
    
    for param in ['duty_station']:    
        if event.get(param) is None:
            raise Exception(f'Event parameter "{param}" is required')
    
    gdoc_dlx.run(
        station=event['duty_station'],
        retro=True
    )

    return {
        'status_code': 200
    }