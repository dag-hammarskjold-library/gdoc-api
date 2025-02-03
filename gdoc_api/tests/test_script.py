import pytest
from gdoc_api import Gdoc
from gdoc_api.scripts import gdoc_dlx

def test_args():
    # Test that args provided to function call are correctly converted to
    # sys.argv

    params = ('station', 'date', 'symbol', 'language', 'overwrite', 'recursive', 'connection_string', 'database', 's3_bucket', 'save_as', 'data_only')
    bools = ('recursive', 'overwrite', 'data_only')

    kwargs = {
        'station': 'NY',
        'date': '1970-01-01',
        'recursive': True,
        'overwrite': False
    }

    args = gdoc_dlx.get_args(**kwargs)
    
    assert args.station == 'NY'
    assert args.date == '1970-01-01'
    assert args.recursive
    assert not args.overwrite
    assert not args.data_only
