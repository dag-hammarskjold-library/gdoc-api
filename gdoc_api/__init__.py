import os, logging, requests, urllib, json, re
from datetime import datetime, timezone
from tempfile import TemporaryFile
from zipfile import ZipFile
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO)

API_URL = 'https://gdoc.un.org/api/ods/getdocuments' # set here so it can be changed for testing
TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')

class Gdoc():
    def __init__(self, *, username, password):
        self.base = API_URL
        self.parameters = {
            'dateFrom': '',
            'dateTo': '',
            'dutyStation': '',
            'includeFiles': '',
            'symbol': ''
        }
        self._data = {}
        self._zipfile = None # ZipFile https://docs.python.org/3/library/zipfile.html#zipfile-objects
        
        # authenticate
        if 'GDOC_API_TESTING' not in os.environ:
            scope = ["gDoc1APIAccess", "gDocFilesAPIAccess"]
            auth = HTTPBasicAuth(username, password)
            client = BackendApplicationClient(client_id=password)
            oauth = OAuth2Session(client=client, scope=scope)
        
            self.token = oauth.fetch_token(
                token_url='https://conferences.unite.un.org/ucid/connect/token', 
                auth=auth, 
                scope=scope
            )
        
    @property
    def data(self):
        if self._data:
            return self._data

        self.download()
        
        return self._data
    
    @property
    def zipfile(self):
        if self._zipfile:
            return self._zipfile
        
        self.download()
        
        return self._zipfile
        
    def set_param(self, name, value):
        self.parameters[name] = value

    def download(self):
        temp = TemporaryFile('wb+')
        url = self.base + '?' + '&'.join(map(lambda x: '{}={}'.format(x[0], x[1]), self.parameters.items()))
        logging.info(url)
        headers = {"Authorization": f"Bearer {self.token['access_token']}"} if 'GDOC_API_TESTING' not in os.environ else None
        response = requests.get(url, stream=True, headers=headers)
        
        if response.status_code == 200:
            logging.info('OK')
            
            for chunk in response.iter_content(8192):
                temp.write(chunk)
        else:
            logging.error(response.text)
            raise Exception(response.text)
                
        self._zipfile = ZipFile(temp)
        
        with self._zipfile.open('export.txt') as datafile:
            self._data = json.loads(datafile.read())
            
    def iter_files(self, callback):
        for name in self.zipfile.namelist():
            match = re.match(r'[A-Z]+(\d+)\.pdf$', name)

            if match:
                ods_num = int(match.group(1))
                file_data = next(filter(lambda x: x['odsNo'] == ods_num, self.data), None)
                
                if file_data is None:
                    logging.warning('Data for "{}" not found in zip file'.format(name))
                    
                yield callback(self.zipfile.open(name), file_data)
            elif name[-4:] == '.pdf':
                logging.warn(f'{name} not found')
                
class Schema():
    pass
