import sys, re, logging
from argparse import ArgumentParser
from dlx import DB as DLX
from dlx.file import S3, File, Identifier, FileExists, FileExistsConflict
from gdoc_api import Gdoc

logging.basicConfig(filename='log', level=logging.INFO)
sys.stderr = open('log', 'a')
logging.info(sys.argv)

def get_args():
    parser = ArgumentParser(prog='gdoc-dlx')
    
    # required
    parser.add_argument('--dlx_connect', required=True, help='MongoDB connection string')
    parser.add_argument('--s3_key_id', required=True)
    parser.add_argument('--s3_key', required=True)
    parser.add_argument('--s3_bucket', required=True)
    parser.add_argument('--gdoc_api_username', required=True)
    parser.add_argument('--gdoc_api_password', required=True)
    parser.add_argument('--gdoc_username', required=True)
    parser.add_argument('--gdoc_password', required=True)
    parser.add_argument('--station', required=True, choices=['NY', 'GE'])
    
    # at least one required
    c = parser.add_mutually_exclusive_group(required=True)
    c.add_argument('--date', help='YYYY-MM-DD')
    c.add_argument('--symbol')
    
    # optional
    parser.add_argument('--language', choices=['A', 'C', 'E', 'F', 'R', 'S', 'O'])
    parser.add_argument('--overwrite', action='store_true', help='ignore conflicts and overwrite exisiting DLX data')
    
    return parser.parse_args()

def set_log():
    args = get_args()
    
    

###

def run():
    args = get_args()
    
    if not args.date and not args.symbol:
        raise Exception('--symbol or --date required')
        
    if args.language and not args.symbol:
        raise Exception('--language requires --symbol')
    
    DLX.connect(args.dlx_connect)    
    S3.connect(args.s3_key_id, args.s3_key, args.s3_bucket)

    g = Gdoc(
        api_username=args.gdoc_api_username, 
        api_password=args.gdoc_api_password, 
        username=args.gdoc_username,
        password=args.gdoc_password,
        station=args.station
    )
    
    g.set_param('Symbol', args.symbol or '')
    g.set_param('DateFrom', args.date or '')
    g.set_param('DateTo', args.date or '')
    g.set_param('DutyStation', args.station or '')
    
    def upload(fh, data):
        symbols = [data['symbol1']]
        
        if data['symbol2'] and not data['symbol2'].isspace():
            symbols.append(data['symbol2'])
    
        if any([re.search(r'JOURNAL', x) for x in symbols]):
            logging.info('skipping {}'.format(symbols))
            return
        
        identifiers = [Identifier('symbol', x) for x in filter(None, symbols)]
        lang = {'A': 'AR', 'C': 'ZH', 'E': 'EN', 'F': 'FR', 'R': 'RU', 'S': 'ES', 'G': 'DE'}[data['languageId']]    
        
        if args.language and lang != args.language.upper():
            logging.info('Skipping ' + lang)
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
                source='gdoc-importx-' + g.station,
                overwrite=overwrite
            )
        except FileExistsConflict as e:
            logging.warning(f'{symbols} {languages} {e.message}')
        except FileExists:
            logging.info(f'{symbols} {languages} is already in the system')
        except Exception as e:
            raise e
            
    for result in g.iter_files(upload):
        if result:
            logging.info(f'OK - {result.id} {[x.value for x in result.identifiers]} {result.languages}')
    
    logging.info('Done')

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