import sys, re, json, boto3
from argparse import ArgumentParser
from dlx import DB as DLX
from dlx.file import S3, File, Identifier, FileExists, FileExistsConflict
from gdoc_api import Gdoc

def get_args():
    parser = ArgumentParser(prog='gdoc-dlx')
    
    r = parser.add_argument_group('required')
    r.add_argument('--station', required=True, choices=['NY', 'GE'])
    r.add_argument('--date', required=True, help='YYYY-MM-DD')

    nr = parser.add_argument_group('not required')
    nr.add_argument('--symbol', help='get only the files for the specified symbol')
    nr.add_argument('--language', choices=['A', 'C', 'E', 'F', 'R', 'S', 'G'], help='get only the files for the specified language')
    nr.add_argument('--overwrite', action='store_true', help='ignore conflicts and overwrite exisiting DLX data')
    nr.add_argument('--recursive', action='store_true', help='download the files one synbol at a time')

    # get from AWS if not provided
    ssm = boto3.client('ssm')
    
    def param(name):
        return ssm.get_parameter(Name=name)['Parameter']['Value']
    
    c = parser.add_argument_group(
        title='credentials', 
        description='these arguments are supplied by AWS SSM if AWS credentials are configured',
    )
    c.add_argument('--connection_string', default=param('prodISSU-admin-connect-string'))
    c.add_argument('--database', default=param('prodISSU-admin-database-name'))
    c.add_argument('--s3_bucket', default=param('dlx-s3-bucket'))
    c.add_argument('--gdoc_api_username', default=json.loads(param('gdoc-api-secrets'))['username'])
    c.add_argument('--gdoc_api_password', default=json.loads(param('gdoc-api-secrets'))['password'])

    return parser.parse_args()

def set_log():
    pass
    
###

def run(*, station=None, date=None, symbol=None, language=None, overwrite=None, recursive=None, **kwargs):
    if station or date:
        sys.argv = [sys.argv[0]]
        sys.argv.append(f'--station={station}')
        sys.argv.append(f'--date={date}')

    if symbol: sys.argv.append(f'--symbol={symbol}')
    if language: sys.argv.append(f'--language={language}')
    if overwrite: sys.argv.append('--overwrite')
    if recursive: sys.argv.append('--recursive')
        
    if kwargs.get('s3_bucket'):
        sys.argv.append(f'--s3_bucket={kwargs["s3_bucket"]}')
       
    args = get_args()
    
    if not args.date and not args.symbol:
        raise Exception('--symbol or --date required')
        
    if args.language and not args.symbol:
        raise Exception('--language requires --symbol')
    
    DLX.connect(args.connection_string, database=args.database) 
    S3.connect(bucket=args.s3_bucket) # not needed since AWS credentials are already in place
    
    g = Gdoc(username=args.gdoc_api_username, password=args.gdoc_api_password)
    g.set_param('symbol', args.symbol or '')
    g.set_param('dateFrom', args.date or '')
    g.set_param('dateTo', args.date or '')
    g.set_param('dutyStation', args.station or '')

    if not args.recursive:
        #g.set_param('includeFiles', 'true')
        g.set_param('DownloadFiles', 'Y')
    else:
        seen = {}
        
        for data in g.data:
            symbol = symbol=data['symbol1']
            
            if seen.get(symbol):
                continue
            
            run(station=args.station, date=args.date, symbol=symbol)
            seen[symbol] = True;

        return
      
    def upload(fh, data):
        # this function is for use as the callback in Gdoc.iter_files

        if data['distributionType'] == 'RES':
            # printing to STDOUT allows caputre in Cloudwatch. Cloudwatch queries can parse JSON strings for searching the logs
            print(json.dumps({'warning': 'Skipping document with distribution type "RES"', 'symbol': data['symbol1']}))
            
            return
        
        symbols = [data['symbol1']]
        
        if data['symbol2'] and not data['symbol2'].isspace():
            symbols.append(data['symbol2'])
    
        if any([re.search(r'JOURNAL', x) for x in symbols]):
            return
        
        lang = {'A': 'AR', 'C': 'ZH', 'E': 'EN', 'F': 'FR', 'R': 'RU', 'S': 'ES', 'G': 'DE'}[data['languageId']]
        
        if args.language and args.language.upper() != data['languageId']:
            return
        
        identifiers = [Identifier('symbol', x) for x in filter(None, symbols)]
        languages = [lang]
        overwrite = True if args.overwrite else False

        try:
            result = File.import_from_handle(
                fh,
                filename=File.encode_fn(list(filter(None, symbols)), lang, 'pdf'),
                identifiers=identifiers,
                languages=languages,
                mimetype='application/pdf',
                source='gdoc-dlx-' + args.station,
                overwrite=overwrite
            )

            # log in DB
            DLX.handle['gdoc_log'].insert_one(
                {
                    'imported': True,
                    'gdoc_station': args.station,
                    'gdoc_date': args.date,
                    'symbols': symbols,
                    'languages': languages,
                    'file_id': result.id
                }
            )

            return result
        except FileExistsConflict as e:
            to_log = {'warning': e.message, 'data': {'symbols': symbols, 'language': languages}}
            print(json.dumps(to_log))
        except FileExists:
            to_log = {'info': 'Already in the system', 'data': {'symbols': symbols, 'language': languages}}
            print(json.dumps(to_log))
        except Exception as e:
            to_log = {'error': '; '.join(re.split('[\r\n]', str(e))), 'data': {'symbols': symbols, 'languages': languages}}
            print(json.dumps(to_log))

        # log in DB
        DLX.handle['gdoc_log'].insert_one(
            {
                'imported': False,
                'message': to_log,
                'gdoc_station': args.station,
                'gdoc_date': args.date,
                'symbols': symbols,
                'languages': languages,
                'file_id': None
            }
        )
    
    i = 0
    
    try:
        # Gdoc.iter_files() takes a callback function as its only argument
        for result in g.iter_files(upload):
            i += 1
            
            if isinstance(result, File):
                print(json.dumps({'info': 'OK', 'data': {'checksum': result.id, 'symbols': [x.value for x in result.identifiers], 'languages': result.languages}}))

                # todo: create the bib record if it doesn't already exist
                

    except Exception as e:
        print(json.dumps({'error': '; '.join(re.split('[\r\n]', str(e)))}))
        
    if i == 0:
        print(json.dumps({'info': 'No results', 'data': {'station': args.station, 'date': args.date, 'symbols': args.symbol, 'language': args.language}}))
    
###

if __name__ == '__main__':
    run()
