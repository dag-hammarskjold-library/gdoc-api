from gdoc_api.scripts import gdoc_dlx
import sys, datetime

def handler(event, context):
    print(f"Processing {event}")
    
    for param in ['duty_station', 'days_ago']:    
        if event.get(param) is None:
            raise Exception(f'Event parameter "{param}" is required')
    
    today = datetime.date.today()
    date = today - datetime.timedelta(days=event['days_ago'])
    gdoc_dlx.run(station=event['duty_station'], date=date, recursive=True)

    return {
        'status_code': 200
    }