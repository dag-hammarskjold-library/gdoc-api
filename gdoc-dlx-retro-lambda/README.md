
### About

This is a Lambda function for running gdoc-dlx-retro on an automated schedule. Once it's been run for a historical range, it should never need to be run again.

### Deployment 

This describes how to deploy this function to AWS Lambda using the Python library [python-lambda](https://pypi.org/project/python-lambda/). The files in this directory are the standard files necessary for deploying Python code to Lambda.

AWS credentials must be configured in the deployment environment. 

1. Navigate to this directory (`gdoc-api/gdoc-dlx-retro-lambda`) 
2. Make sure a virtual environment (venv) is activated.
3. ```pip install -r requirements.txt```
4. ```lambda deploy```

Note that once the Lambda function is deployed, it will not run until it is "invoked". [Several methods exist to invoke the function](https://docs.aws.amazon.com/lambda/latest/dg/lambda-invocation.html).

### Running the Lambda function locally (for development/testing purposes)

```lambda invoke -v --event-file=event.json```