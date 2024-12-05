import sys, re, json, boto3, os
from argparse import ArgumentParser
from dlx import DB as DLX
from dlx.marc import Bib, Query, Condition, Or
from dlx.file import S3, File, Identifier, FileExists, FileExistsConflict
from gdoc_api import Gdoc

def get_args(**kwargs):
    parser = ArgumentParser(prog='gdoc-dlx')
    
    r = parser.add_argument_group('required')
    r.add_argument('--station', required=True, choices=['NY', 'GE', 'Vienna', 'Beirut', 'Bangkok', 'Nairobi'])
    r.add_argument('--date', required=True, help='YYYY-MM-DD')

    nr = parser.add_argument_group('not required')
    nr.add_argument('--symbol', help='get only the files for the specified symbol')
    nr.add_argument('--language', choices=['A', 'C', 'E', 'F', 'R', 'S', 'G'], help='get only the files for the specified language')
    nr.add_argument('--overwrite', action='store_true', help='ignore conflicts and overwrite exisiting DLX data')
    nr.add_argument('--recursive', action='store_true', help='download the files one symbol at a time')
    nr.add_argument('--data_only', action='store_true', help='get only the data without downloading the files and print it to STDOUT')
    nr.add_argument('--create_bibs', action='store_true', help='Create bib record for symbol if it doesn\'t exist')

    # get from AWS if not provided
    ssm = boto3.client('ssm')
    # Can be "qa" or "prod"
    env = os.getenv("GDOC_ENV", "qa")
    print("Connecting to GDOC:",env)
    
    def param(name):
        return ssm.get_parameter(Name=name)['Parameter']['Value']
    
    c = parser.add_argument_group(
        title='credentials', 
        description='these arguments are supplied by AWS SSM if AWS credentials are configured',
    )

    connect_string_param = json.loads(param(f'gdoc-{env}-api-secrets'))['connect_string_param']

    c.add_argument('--connection_string', default=param(connect_string_param))
    c.add_argument('--database', default=json.loads(param(f'gdoc-{env}-api-secrets'))['database_name'])
    c.add_argument('--s3_bucket', default=json.loads(param(f'gdoc-{env}-api-secrets'))['bucket'])
    c.add_argument('--gdoc_token_url', default=json.loads(param(f'gdoc-{env}-api-secrets'))['token_url'])
    c.add_argument('--gdoc_api_url', default=json.loads(param(f'gdoc-{env}-api-secrets'))['api_url'])
    c.add_argument('--gdoc_ocp_apim_subscription_key', default=json.loads(param(f'gdoc-{env}-api-secrets'))['ocp_apim_subscription_key'])
    c.add_argument('--gdoc_client_id', default=json.loads(param(f'gdoc-{env}-api-secrets'))['client_id'])
    c.add_argument('--gdoc_client_secret', default=json.loads(param(f'gdoc-{env}-api-secrets'))['client_secret'])
    c.add_argument('--gdoc_scope', default=json.loads(param(f'gdoc-{env}-api-secrets'))['scope'])

    # Deprecated, replaced by client ID and secret
    #c.add_argument('--gdoc_api_username', default=json.loads(param('gdoc-{env}-api-secrets'))['username'])
    #c.add_argument('--gdoc_api_password', default=json.loads(param('gdoc-{env}-api-secrets'))['password'])

    # If running as a function, convert the function args to command line args
    # so they can be parsed by argparse
    if kwargs:
        sys.argv = [sys.argv[0]]
        params = ('station', 'date', 'symbol', 'language', 'overwrite', 'rescursive', 'connection_string', 'database', 's3_bucket', 'data_only', 'create_bibs')

        for param in ('station', 'date'):
            if param not in params:
                raise Exception(f'Required param {param}')

        for param, arg in kwargs.items():
            if param not in params:
                raise Exception(f'Invalid argument: "{param}"')

            if param in ('overwrite', 'recursive', 'data_only', 'create_bibs'):
                # boolean args
                if arg == True:
                    sys.argv.append(f'--{param}')
            else:
                sys.argv.append(f'--{param}={arg}')

    return parser.parse_args()

def set_log():
    pass
    
###

def run(**kwargs): # *, station, date, symbol=None, language=None, overwrite=None, recursive=None, connection_string=None, database=None, s3_bucket=None, create_bibs=None):
    args = get_args(**kwargs)
    
    if not args.date and not args.symbol:
        raise Exception('--symbol or --date required')
        
    if args.language and not args.symbol:
        raise Exception('--language requires --symbol')

    DLX.connect(args.connection_string, database=args.database) 
    S3.connect(bucket=args.s3_bucket) # not needed since AWS credentials are already in place
    
    g = Gdoc(
        client_id=args.gdoc_client_id, 
        client_secret=args.gdoc_client_secret,
        token_url=args.gdoc_token_url,
        api_url=args.gdoc_api_url,
        ocp_apim_subscription_key=args.gdoc_ocp_apim_subscription_key,
        scope=args.gdoc_scope
    )
    g.set_param('symbol', args.symbol or '')
    g.set_param('dateFrom', args.date or '')
    g.set_param('dateTo', args.date or '')
    g.set_param('dutyStation', args.station or '')

    if args.recursive:
        if args.data_only:
            raise Exception('--data_only not compatible with --recursive')
        
        # call the run function for each indvidual symbol
        seen = {}
        
        for data in g.data:
            symbol = symbol=data['symbol1']
            
            if seen.get(symbol):
                continue
            
            run(
                connection_string=args.connection_string,
                database=args.database,
                s3_bucket=args.s3_bucket,
                station=args.station,
                date=args.date,
                symbol=symbol,
                overwrite=args.overwrite
            )

            seen[symbol] = True;
        
        return
    elif args.data_only:
        g.set_param('DownloadFiles', 'N')
        print(json.dumps(g.data))
        exit()
    else:
        g.set_param('DownloadFiles', 'Y')
      
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
        import_result = None

        try:
            import_result = File.import_from_handle(
                fh,
                filename=File.encode_fn(list(filter(None, symbols)), lang, 'pdf'),
                identifiers=identifiers,
                languages=languages,
                mimetype='application/pdf',
                source='gdoc-dlx-' + args.station,
                overwrite=overwrite
            )
        except FileExistsConflict as e:
            to_log = {'warning': e.message, 'data': {'symbols': symbols, 'language': languages}}
            print(json.dumps(to_log))
        except FileExists:
            to_log = {'info': 'Already in the system', 'data': {'symbols': symbols, 'language': languages}}
            print(json.dumps(to_log))
        except Exception as e:
            to_log = {'error': '; '.join(re.split('[\r\n]', str(e))), 'data': {'symbols': symbols, 'languages': languages}}
            print(json.dumps(to_log))

        if import_result:
            # log in DB
            DLX.handle['gdoc_log'].insert_one(
                {
                    'imported': True,
                    'gdoc_station': args.station,
                    'gdoc_date': args.date,
                    'symbols': symbols,
                    'languages': languages,
                    'file_id': import_result.id
                }
            )

            return import_result
        else:
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
    
    # group the data by symbol for bib record creation later
    symbols_index = {}

    for data in g.data:
        symbol = data.get('symbol1')
        symbols_index.setdefault(symbol, [])
        symbols_index[symbol].append(data)
    
    i = 0
    
    try:
        # Gdoc.iter_files() takes a callback function as its only argument
        for result in g.iter_files(upload):
            i += 1
            
            if isinstance(result, File):
                symbols = [x.value for x in result.identifiers]
                print(json.dumps({'info': 'OK', 'data': {'checksum': result.id, 'symbols': symbols, 'languages': result.languages}}))
            
                # create bib record if option enabled
                if args.create_bibs is None or result.languages[0].lower() != 'en':
                    pass
                elif bib := Bib.from_query(Query(Or(Condition('191', {'a': {'$in': symbols}}), Condition('191', {'z': {'$in': symbols}})))):
                    print('Bib record for {symbols} already exists')
                else:
                    new_bib = Bib()

                    for symbol in symbols:
                        new_bib.set('191', 'a', symbol, address='+')

                    new_bib.set('245', 'a', 'Work in progress')

                    titles = [x.get('title') for x in symbols_index[symbols[0]]]
                    
                    for title in titles:
                        if title not in new_bib.get_values('246', 'a'):
                            new_bib.set('246', 'a', title, address='+')

                    new_bib.commit(user='gDoc import')
                    print(json.dumps({'info': 'Created new bib', 'data': {'record_id': new_bib.id}}))
    except Exception as e:
        print(json.dumps({'error': '; '.join(re.split('[\r\n]', str(e)))}))
        
    if i == 0:
        print(json.dumps({'info': 'No results', 'data': {'station': args.station, 'date': args.date, 'symbols': args.symbol, 'language': args.language}}))

###

if __name__ == '__main__':
    run()
