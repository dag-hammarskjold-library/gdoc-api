import pytest, os
from gdoc_api import Gdoc
from gdoc_api.scripts import gdoc_dlx
from moto import mock_aws
import boto3, os, json

os.environ.update(
    {
        'DLX_ENV': 'testing',
        'GDOC_ENV': 'testing',
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }
)

@pytest.fixture(scope="function")
def ssm_mock():
    with mock_aws():
        ssm = boto3.client("ssm")
        # the mock AWS SSM data to be fetched as the arguments for the script
        ssm.put_parameter(
            Name="gdoc-testing-api-secrets",
            Value=json.dumps({
                "token_url": "https://foo.bar.baz/oauth2/v2.0/token",
                "api_url": "https://foo.bar.baz/GetODSDocuments",
                "content_type": "application/x-www-form-urlencoded",
                "ocp_apim_subscription_key": "test_sub_key",
                "grant_type": "Client Credentials",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "scope": ["api://test_scope/.default"],
            }),
            Type="String"
        )
        yield ssm

def test_args(ssm_mock):
    # Test that args provided to function call are correctly converted to ArgumentParser args.
    # SSM is required to fetch gdoc creds

    kwargs = {
        'station': 'NY',
        'date': '1970-01-01',
        'recursive': True,
        'overwrite': False
    }

    args = gdoc_dlx.get_args(**kwargs)
    gdoc_params = ('gdoc_token_url', 'gdoc_api_url', 'gdoc_ocp_apim_subscription_key', 'gdoc_client_id', 'gdoc_client_secret', 'gdoc_scope')

    for name in gdoc_params:
        # ensure the godoc credentials have been retrieved
        assert getattr(args, (name))

    assert args.connection_string == 'dummy'

    assert args.station == 'NY'
    assert args.date == '1970-01-01'
    assert args.recursive
    assert not args.overwrite
    assert not args.data_only

    kwargs.update({'symbol': 'A/RES/1'})
    kwargs.update({'language': 'E'})
    args = gdoc_dlx.get_args(**kwargs)
    assert args.symbol == 'A/RES/1'
    assert args.language == 'E'
