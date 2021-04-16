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
```bash
gdoc-dlx --help
```

```bash
gdoc-dlx --station=NY --date=2021-01-03
```

As a function (Python):
```python
from gdoc_api.scripts import gdoc_dlx

gdoc_dlx.run(station=NY, date=2021-01-03)
```
