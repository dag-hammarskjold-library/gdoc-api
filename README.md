#### Installation
From the command line:
```bash
pip install git+https://github.com/dag-hammarskjold-library/gdoc-api
```

#### Classes
> #### Gdoc
Usage (Python):
```python
from gdoc_api import Gdoc

g = Gdoc(username=DHL, password=<password>)
g.set_param('dateFrom', '2020-12-31')
g.set_param('dateTo', '2020-12-31')
g.set_param('dutyStation', 'NY')

def todo(fileobj, data):
    print(f'Processsed {data["odsNo"]}')
    
g.iter_files(todo)
```

#### Scripts
> #### gdoc-dlx
Gets files from Gdoc and imports them into DLX

Usage (command line):
```
usage: 
    gdoc-dlx [-h] --station {NY,GE} (--date DATE | --symbol SYMBOL) [--language {A,C,E,F,R,S,O}] [--overwrite]

optional arguments:
  -h, --help            show this help message and exit
  --dlx_connect DLX_CONNECT
                        MongoDB connection string
  --s3_key_id S3_KEY_ID
  --s3_key S3_KEY
  --s3_bucket S3_BUCKET
  --gdoc_api_username GDOC_API_USERNAME
  --gdoc_api_password GDOC_API_PASSWORD
  --gdoc_username GDOC_USERNAME
  --gdoc_password GDOC_PASSWORD
  --station {NY,GE}
  --date DATE           YYYY-MM-DD
  --symbol SYMBOL
  --language {A,C,E,F,R,S,O}
  --overwrite           Ignore conflicts and overwrite exisiting DLX data
```
