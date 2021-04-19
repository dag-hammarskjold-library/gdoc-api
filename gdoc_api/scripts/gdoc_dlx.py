import sys, re, json, boto3
from argparse import ArgumentParser
from dlx import DB as DLX
from dlx.file import S3, File, Identifier, FileExists, FileExistsConflict
from gdoc_api import Gdoc

def get_args():
    parser = ArgumentParser(prog='gdoc-dlx')
    
    # required
    parser.add_argument('--station', required=True, choices=['NY', 'GE'])
    
    # at least one required
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--date', help='YYYY-MM-DD')
    g.add_argument('--symbol')
    
    # not required
    parser.add_argument('--language', choices=['A', 'C', 'E', 'F', 'R', 'S', 'O'])
    parser.add_argument('--overwrite', action='store_true', help='Ignore conflicts and overwrite exisiting DLX data')
    
    # get from AWS if not provided
    ssm = boto3.client('ssm')
    
    def param(name):
        return ssm.get_parameter(Name=name)['Parameter']['Value']

    parser.add_argument('--dlx_connect', default=param('connect-string'))
    parser.add_argument('--s3_bucket', default=param('dlx-s3-bucket'))
    parser.add_argument('--gdoc_api_username', default=json.loads(param('gdoc-api-secrets'))['username'])
    parser.add_argument('--gdoc_api_password', default=json.loads(param('gdoc-api-secrets'))['password'])

    return parser.parse_args()

def set_log():
    pass
    
###

def run(*, station=None, date=None, language=None, overwrite=None, **kwargs):
    if station or date:
        sys.argv = [sys.argv[0]]
        sys.argv.append(f'--station={station}')
        sys.argv.append(f'--date={date}')
    
    if language: sys.argv.append(f'--language={language}')
    if overwrite: sys.argv.append('--overwrite')
    
    if kwargs.get('s3_bucket'):
        sys.argv.append(f'--s3_bucket={kwargs["s3_bucket"]}')
       
    args = get_args()
    
    if not args.date and not args.symbol:
        raise Exception('--symbol or --date required')
        
    if args.language and not args.symbol:
        raise Exception('--language requires --symbol')
    
    DLX.connect(args.dlx_connect)    
    S3.connect(bucket=args.s3_bucket) # this may change
    
    g = Gdoc(username=args.gdoc_api_username, password=args.gdoc_api_password)
    g.set_param('symbol', args.symbol or '')
    g.set_param('dateFrom', args.date or '')
    g.set_param('dateTo', args.date or '')
    g.set_param('dutyStation', args.station or '')
    g.set_param('includeFiles', 'true')
      
    def upload(fh, data):
        symbols = [data['symbol1']]
        
        if data['symbol2'] and not data['symbol2'].isspace():
            symbols.append(data['symbol2'])
    
        if any([re.search(r'JOURNAL', x) for x in symbols]):
            return
        
        identifiers = [Identifier('symbol', x) for x in filter(None, symbols)]
        lang = {'A': 'AR', 'C': 'ZH', 'E': 'EN', 'F': 'FR', 'R': 'RU', 'S': 'ES', 'G': 'DE'}[data['languageId']]
        
        if args.language and lang != args.language.upper():
            return
        
        languages = [lang]
        overwrite = True if args.overwrite else False

        try:
            return File.import_from_handle(
                fh,
                filename=encode_fn(list(filter(None, symbols)), languages[0], 'pdf'),
                identifiers=identifiers,
                languages=languages,
                mimetype='application/pdf',
                source='gdoc-dlx-' + args.station,
                overwrite=overwrite
            )
        except FileExistsConflict as e:
            print(json.dumps({'warning': e.message, 'data': {'symbols': symbols, 'language': languages}}))
        except FileExists:
            print(json.dumps({'info': 'Already in the system', 'data': {'symbols': symbols, 'language': languages}}))
        except Exception as e:
            print(json.dumps({'error': '; '.join(re.split('[\r\n]', str(e))), 'data': {'symbols': symbols, 'languages': languages}}))
            raise e
    
    i = 0
    
    for result in g.iter_files(upload):
        if result:
            print(json.dumps({'info': 'OK', 'data': {'checksum': result.id, 'symbols': [x.value for x in result.identifiers], 'languages': result.languages}}))
        
        i += 1
        
    if i == 0:
        print(json.dumps({'info': 'No results', 'data': {'station': args.station, 'date': args.date, 'symbols': args.symbol, 'language': args.language}}))

### util
        
from dlx.util import ISO6391

def encode_fn(symbols, language, extension):
    ISO6391.codes[language.lower()]
    symbols = [symbols] if isinstance(symbols, str) else symbols
    xsymbols = [sym.translate(str.maketrans(' /[]*:;', '__^^!#%')) for sym in symbols]

    return '{}-{}.{}'.format('&'.join(xsymbols), language.upper(), extension)
    
###

if __name__ == '__main__':
    run()
