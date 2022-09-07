import os, requests, urllib, json, re
from datetime import datetime, timezone
from tempfile import TemporaryFile
from zipfile import ZipFile
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth

#API_URL = 'https://gdoc.un.org/api/ods/getdocuments' # set here so it can be changed for testing
API_URL = 'http://conferences.unite.un.org/gdoc-data/api/odsdata/getodsdocuments'
TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')

class Gdoc():
    def __init__(self, *, username, password):
        self.base = API_URL
        self.parameters = {
            'dateFrom': '',
            'dateTo': '',
            'dutyStation': '',
            'DownloadFiles': '',
            'symbol': ''
        }
        self._data = {}
        self._zipfile = None # ZipFile https://docs.python.org/3/library/zipfile.html#zipfile-objects
        
        # authenticate
        if 'GDOC_API_TESTING' not in os.environ:
            scope = ["gDoc2DataAPIAccess", "gDocFilesAPIAccess"]
            auth = HTTPBasicAuth(username, password)
            client = BackendApplicationClient(client_id=password)
            oauth = OAuth2Session(client=client, scope=scope)
        
            self.token = oauth.fetch_token(
                token_url='https://conferences.unite.un.org/ucid4/connect/token', 
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
        headers = {"Authorization": f"Bearer {self.token['access_token']}"} if 'GDOC_API_TESTING' not in os.environ else None
        print(json.dumps({'info': f'Getting {url}'}))
        response = requests.get(url, stream=True, headers=headers)
        
        if response.status_code == 200:
            print(json.dumps({'info': 'Connection established'}))
            
            for chunk in response.iter_content(8192):
                temp.write(chunk)
                
            self._zipfile = ZipFile(temp)
        
            with self._zipfile.open('export.txt') as datafile:
                self._data = json.loads(datafile.read())
                
            for d in self._data:
                found = list(filter(lambda x: re.match(f'[A-Z]+({d["jobId"]}.pdf)', x), self.zipfile.namelist()))
            
                if self.parameters['DownloadFiles'] == 'Y' and len(found) == 0:
                    print(json.dumps({'warning': f'File for {d["symbol1"]} not found in feed'}))
        else:
            raise Exception('API error:\n' + response.text)
            
            
    def iter_files(self, callback):
        for name in self.zipfile.namelist():
            match = re.match(r'[A-Z]+(\d+)\.pdf$', name)

            if match:
                # This changed to jobId in gDoc 2
                ods_num = int(match.group(1))
                file_data = next(filter(lambda x: x['jobId'] == str(ods_num), self.data), None)
                
                if file_data is None:
                    print(json.dumps({'warning': f'Data for "{name}" not found in zip file', 'data': file_data}))
                    
                yield callback(self.zipfile.open(name), file_data)
            elif name[-4:] == '.pdf':
                print(json.dumps({'warning': f'File "{name}" not found in zip file', 'data': file_data}))
                
                
class Schema():
    pass
