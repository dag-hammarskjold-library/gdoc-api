import logging, requests, urllib, json, re
from datetime import datetime, timezone
from tempfile import TemporaryFile
from zipfile import ZipFile

logging.basicConfig(filename='log', level=logging.INFO)

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')

class Gdoc():
    def __init__(self, api_username, api_password, username, password, **kwargs):
        self.station = kwargs.get('station') or ''
        self._data = {} 
        self._zipfile = None # ZipFile https://docs.python.org/3/library/zipfile.html#zipfile-objects
        self.base = 'https://conferenceservices.un.org/ICTSAPI/ODS/GetODSDocumentsV2'
        self.parameters = {
            'APIUserName': api_username,
            'APIPassword': api_password,
            'UserName': username,
            'Password': password,
            'AppName': 'gDoc',
            'DstOff': 'Y',
            'LocalDate': TODAY,
            'DownloadFiles': 'Y',
            'Odsstatus': 'Y',
            'ResultType': 'Released',
            'DateFrom': '',
            'DateTo': '',
            'Symbol': '',
            'DutyStation': ''
        }
        
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
        response = requests.get(url, stream=True)
        
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
            match = re.match(r'[A-Z](\d+)\.pdf$', name)

            if match:
                ods_num = int(match.group(1))
                file_data = next(filter(lambda x: x['odsNo'] == ods_num, self.data), None)
                
                if file_data is None:
                    logging.warning('Data for "{}" not found in zip file'.format(name))
                    
                yield callback(self.zipfile.open(name), file_data)
