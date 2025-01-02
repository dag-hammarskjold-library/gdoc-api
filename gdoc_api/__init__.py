import os, requests, urllib, json, re, shutil
from typing import Optional, Self, Callable, Iterator
from datetime import datetime, timezone
from tempfile import TemporaryFile
from zipfile import ZipFile
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
class Gdoc():
    def __init__(self, *, client_id, client_secret, token_url,
        api_url, ocp_apim_subscription_key, scope):

        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.api_url = api_url
        self.ocp_apim_subscription_key = ocp_apim_subscription_key
        self.scope = scope
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
            auth = HTTPBasicAuth(self.client_id, self.client_secret)
            client = BackendApplicationClient(client_id=self.client_secret) 
            oauth = OAuth2Session(client=client, scope=self.scope)
        
            self.token = oauth.fetch_token(
                token_url=self.token_url, 
                auth=auth, 
                scope=self.scope
            )
        
    @property
    def data(self) -> dict:
        if self._data:
            return self._data

        self.download()
        
        return self._data
    
    @property
    def zipfile(self) -> ZipFile:
        """Returns an in-memory ZipFile object containing the API request payload"""

        if self._zipfile:
            return self._zipfile
        
        self.download()
        
        return self._zipfile
        
    def set_param(self, name: str, value: str) -> None:
        """Sets a single param to be used in the gDoc API call"""

        self.parameters[name] = value

    def download(self, save_as: os.PathLike = None) -> Self:
        """Make the API request using the parameters provided and save the
        returned Zip file. The Zip file is stored in memory. If `save_as` is 
        provided, the Zip file is also saved to that localtion on the local disk.
        """

        temp = TemporaryFile('wb+')
        self.tempfile = temp
        url = self.api_url + '?' + '&'.join(map(lambda x: '{}={}'.format(x[0], x[1]), self.parameters.items()))
        
        headers = {
            "Authorization": f"Bearer {self.token['access_token']}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Ocp-Apim-Subscription-Key": self.ocp_apim_subscription_key
        } if 'GDOC_API_TESTING' not in os.environ else None


        print(json.dumps({'info': f'Getting {url}'}))
        response = requests.get(url, stream=True, headers=headers)
        
        if response.status_code == 200:
            print(json.dumps({'info': 'Connection established'}))
            
            for chunk in response.iter_content(8192):
                temp.write(chunk)
                
            self._zipfile = ZipFile(temp)

            if save_as:
                temp.seek(0)
                new_file = open(save_as, 'wb')
                shutil.copyfileobj(temp, new_file)
                new_file.close()
        
            # all zipfiles have export.txt containing the file metadata
            with self._zipfile.open('export.txt') as datafile:
                self._data = json.loads(datafile.read())

            # with API DownloadFiles option, the zipfile should also include files named using data from the metadata
            if self.parameters['DownloadFiles'] == 'Y':
                # check that the file exists in the zipfile uisng the zipfile manifest
                for doc in self._data:
                    found = False

                    # check both jobId and odsNo as the name of the file, as it has varied in the past 
                    for field in ('jobId', 'odsNo'):
                        if any(filter(lambda x: re.match(r'.*?' + doc[field] + r'\.pdf', x), self.zipfile.namelist())):
                            found = True

                    if not found:
                        print(json.dumps({'warning': f'File for {doc["symbol1"]} not found in zip file'}))
        else:
            raise Exception('API error:\n' + response.text)

        return self

    def iter_files(self, callback: Callable) -> Iterator:
        '''For each file named in the zipfile manifest, run the provided callback function using the file object 
        and its and metadata as arguments. This is implemented so that the whole zipfile does not have to be expanded
        at once.'''

        for name in self.zipfile.namelist():
            # filenames contain a series of digits preceeding the file extension that can be matched to the metadata
            match = re.match(r'.*?(\d+)\.pdf$', name)

            if match:
                filename = int(match.group(1))

                # check both jobId and odsNo in the metadata, as the field used has varied in the past
                if file_data := next(filter(lambda x: x['jobId'] == str(filename), self.data), None):
                    yield callback(self.zipfile.open(name), file_data)
                elif file_data := next(filter(lambda x: x['odsNo'] == str(filename), self.data), None):
                    yield callback(self.zipfile.open(name), file_data)
                else:  
                    print(json.dumps({'warning': f'Data for "{name}" not found in zip file'}))   

class Schema():
    pass
