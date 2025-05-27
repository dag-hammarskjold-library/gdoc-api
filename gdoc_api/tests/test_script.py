import pytest
from gdoc_api import Gdoc
from gdoc_api.scripts import gdoc_dlx
from moto import mock_aws
import boto3, os, json

@pytest.fixture(scope="function")
def ssm_mock():
    with mock_aws():
        ssm = boto3.client("ssm")
        # the mock AWS SSM data to be fetched as the arguments for the script
        ssm.put_parameter(
            Name="gdoc-qa-api-secrets",
            Value=json.dumps({
                "token_url": "https://foo.bar.baz/oauth2/v2.0/token",
                "api_url": "https://foo.bar.baz/GetODSDocuments",
                "content_type": "application/x-www-form-urlencoded",
                "ocp_apim_subscription_key": "test_sub_key",
                "grant_type": "Client Credentials",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "scope": ["api://test_scope/.default"],
                "bucket": "test_bucket",
                "database_name": "test_db",
                "connect_string_param": "test-connect-string"
            }),
            Type="String"
        )
        # the database connection string has its own SSM param
        ssm.put_parameter(
            Name="test-connect-string",
            Value="mongodb://foo.bar",
            Type="String"
        )
        yield ssm

def test_args(ssm_mock):
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
