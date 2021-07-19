### Installation
From the command line:
```bash
pip install git+https://github.com/dag-hammarskjold-library/gdoc-api
```

### Classes
> #### Gdoc
##### Usage (Python):
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

### Scripts
> #### gdoc-dlx
Gets files from Gdoc and imports them into DLX. Prints log to STDOUT

##### Usage (command line):
```bash
gdoc-dlx --help
```
```
usage: gdoc-dlx [-h] --station {NY,GE} --date DATE [--symbol SYMBOL] [--language {A,C,E,F,R,S,G}] [--overwrite] [--recursive] [--dlx_connect DLX_CONNECT]
                [--s3_bucket S3_BUCKET] [--gdoc_api_username GDOC_API_USERNAME] [--gdoc_api_password GDOC_API_PASSWORD]

optional arguments:
  -h, --help            show this help message and exit

required:
  --station {NY,GE}
  --date DATE           YYYY-MM-DD

not required:
  --symbol SYMBOL       get only the files for the specified symbol
  --language {A,C,E,F,R,S,G}
                        get only the files for the specified language
  --overwrite           ignore conflicts and overwrite exisiting DLX data
  --recursive           download the files one symbol at a time

credentials:
  these arguments are supplied by AWS SSM if AWS credentials are configured

  --dlx_connect DLX_CONNECT
  --s3_bucket S3_BUCKET
  --gdoc_api_username GDOC_API_USERNAME
  --gdoc_api_password GDOC_API_PASSWORD
```

##### Usage (Python):

Use the `run` function and the parameters specified above in the form of keyword arguments
```python
from gdoc_api.scripts import gdoc_dlx

gdoc_dlx.run(station=NY, date=2021-01-03)	
```
