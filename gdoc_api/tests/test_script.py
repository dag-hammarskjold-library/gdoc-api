import pytest
from gdoc_api import Gdoc
from gdoc_api.scripts import gdoc_dlx
from moto import mock_aws
import boto3, os

@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="function")
def ssm_mock(aws_credentials):
    with mock_aws():
        ssm = boto3.client("ssm")
        ssm.put_parameter(
            Name="gdoc-qa-api-secrets",
            Description="QA parameters for testing",
            Value=""
        )
        yield ssm


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
