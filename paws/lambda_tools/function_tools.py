import os
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3

from paws.utils import zip_to
from paws.s3 import push_to_s3


def delete_function(function_name, aws_profile):
    """
    Delete an AWS Lambda function.

    Parameters
    ----------
    function_name: str
        Name of the Lambda function to delete.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.

    Returns
    -------
    True
    """
    os.environ["AWS_PROFILE"] = aws_profile
    lambda_client = boto3.client("lambda")
    lambda_client.delete_function(FunctionName=function_name)
    return True


def update_lambda_code_from_s3(object_key, bucket_name, aws_profile,
                               function_name):
    """
    Update an AWS Lambda function's code from an existing S3 object.

    Parameters
    ----------
     object_key: str
        AWS S3 object key of layer to deploy.
    bucket_name: str
        AWS S3 bucket name containing `object_key`.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    function_name: str
        Name of the Lambda function to update.

    Returns
    -------
    r: dict
        Response from AWS containing function information.
    """
    os.environ["AWS_PROFILE"] = aws_profile
    lambda_client = boto3.client("lambda")
    r = lambda_client.update_function_code(
        FunctionName=function_name, S3Bucket=bucket_name, S3Key=object_key,
        Publish=True)
    return r


def add_layers_to_function(function_name, layers, aws_profile):
    """
    Add layers to an AWS Lambda function.

    Parameters
    ----------
    function_name: str
        Name of the Lambda function to update.
    layers: list
        List of LayerVersionArns to add to the lambda function.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.

    Returns
    -------
    r: dict
        Response from AWS containing function information.
    """
    os.environ["AWS_PROFILE"] = aws_profile
    lambda_client = boto3.client("lambda")
    r = lambda_client.update_function_configuration(
        FunctionName=function_name, Layers=layers)
    return r


def update_function(function_name, function_path, bucket_name, aws_profile,
                    layers=None):
    """
    Update an AWS Lambda function with code and layers.

    Parameters
    ----------
    function_name: str
        Name of the Lambda function to update.
    function_path: Path or str
        Path of the lambda function. This should be a directory
        containing only the function and other necessary files.
    bucket_name: str
        AWS S3 bucket name to store the zipped function.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    layers: list or None, optional
        List of LayerVersionArns to add to the lambda function. None
        by default.

    Returns
    -------
    r: dict
        Response from AWS containing function information.
    """
    function_path = Path(function_path)
    with TemporaryDirectory() as t:
        t = Path(t)
        zipped = zip_to(function_path, t / "lambda_function.zip", True)
        s3ed = push_to_s3(zipped, bucket_name, aws_profile, create_bucket=True)
    if layers:
        add_layers_to_function(function_name, layers, aws_profile)
    r = update_lambda_code_from_s3(s3ed.key, bucket_name, aws_profile,
                                   function_name)

    return r


def create_function(
        function_name, function_path, bucket_name,
        aws_profile, role,layers=None,
        handler="lambda_function.lambda_handler",
        description="", api_gateway_permission=True,
        env=None):
    """
    Create an AWS Lambda function

    Parameters
    ----------
    function_name: str
        Name of the Lambda function to create.
    function_path: Path or str
        Path of the lambda function. This should be a directory
        containing only the function and other necessary files.
    bucket_name: str
        AWS S3 bucket name to store the zipped function.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    role: str
        Role to assign to the Lambda function. This should be an ARN
        from AWS IAM.
    layers: list or None, optional
        List of LayerVersionArns to add to the lambda function. None
        by default.

    handler: str, optional
        module.function which should run on invocation.
        `lambda_function.lambda_function.lambda_handler` by default.
    description: str, optional
        Description of Lambda function to be created. Blank by default.
    api_gateway_permission: bool, optional
        Should the Lambda function be invocable by the AWS APIGateway?
        True by default.
    env: dict or None, optional
        Dictionary containing environment variables to pass into lambda

    Returns
    -------
    lambda_function: dict
        Response from AWS containing function information.

    """
    os.environ["AWS_PROFILE"] = aws_profile
    client = boto3.client("lambda")

    with TemporaryDirectory() as t:
        t = Path(t)
        zipped = zip_to(function_path, t / "lambda_function.zip")
        s3ed = push_to_s3(zipped, bucket_name, aws_profile, create_bucket=True)
    if not layers:
        layers = []
    if not env:
        env = {}
    lambda_function = client.create_function(
        FunctionName=function_name, Runtime="python3.6", Role=role,
        Handler=handler,
        Code={"S3Bucket": s3ed.bucket_name, "S3Key": s3ed.key},
        Description=description, Layers=layers,
        Environment={
            'Variables': env
        }
    )
    if api_gateway_permission:
        client.add_permission(FunctionName=function_name,
                              Action="lambda:InvokeFunction",
                              StatementId="apigateway",
                              Principal="apigateway.amazonaws.com")
    return lambda_function


def create_lambda_api_link(function_arn, api_name, path_part, stage_name,
                           aws_profile, description=""):
    """
    Create an AWS APIGateway API which allows invocation of, and
    returning of, an existing AWS Lambda function.

    Parameters
    ----------
    function_arn: str
        ARN of AWS Lambda function to use.
    api_name: str
        Name to use for the APIGateway API.
    path_part: str
        Path for the API. This will be present in the form
        `https://api.../path_part/stage_name`.
    stage_name: str
        Path for the API. This will be present in the form
        `https://api.../path_part/stage_name`.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    description: str, optional
        Description of the API to use in AWS. Blank by default.

    Returns
    -------
    url: str
        The url at which the API can be accessed.
    """
    os.environ["AWS_PROFILE"] = aws_profile
    client = boto3.client("apigateway")
    rest_api = client.create_rest_api(name=api_name, description=description)
    rest_api_id = rest_api["id"]
    resources = client.get_resources(restApiId=rest_api_id)
    parent_resource = resources["items"][0]["id"]
    created_resource = client.create_resource(restApiId=rest_api_id,
                                              parentId=parent_resource,
                                              pathPart=path_part)
    created_resource_id = created_resource["id"]
    client.put_method(restApiId=rest_api_id, resourceId=created_resource_id,
                      httpMethod="ANY", authorizationType="NONE")
    uri = ("arn:aws:apigateway:eu-west-1:lambda:path/"
           "2015-03-31/functions/{}/invocations").format(function_arn)
    client.put_integration(restApiId=rest_api_id,
                           resourceId=created_resource_id, httpMethod="ANY",
                           type="AWS_PROXY",
                           integrationHttpMethod="POST", uri=uri)
    client.create_deployment(restApiId=rest_api_id, stageName=stage_name)

    url = "https://{}.execute-api.eu-west-1.amazonaws.com/{}/{}/".format(
        rest_api_id, stage_name, path_part)
    return url


def deploy_function(function_name, function_path, bucket_name, aws_profile,
                    role, layers=None, description="", env=None, make_api=True):
    """
    Create an AWS Lambda function and an AWS APIGateway instance.
    This uses some defaults, for more power see `create_function` and
    `create_lambda_api_link`.

    Parameters
    ----------
    function_name: str
        Name of the Lambda function to create.
    function_path: Path or str
        Path of the lambda function. This should be a directory
        containing only the function and other necessary files.
    bucket_name: str
        AWS S3 bucket name to store the zipped function.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    role: str
        Role to assign to the Lambda function. This should be an ARN
        from AWS IAM.
    layers: list or None, optional
        List of LayerVersionArns to add to the lambda function. None
        by default.
    description: str, optional
        Description of Lambda function and APIGateway instance to be
        created. Blank by default.
    make_api: bool, optional
        Should a new API be created? Useful for testing and deployment
        if it's not needed.

    Returns
    -------
    url: str
        The url at which the API can be accessed.
    """

    f = create_function(function_name, function_path, bucket_name, aws_profile,
                        role, layers, description=description, env=env)
    arn = f["FunctionArn"]
    if make_api:
        url = create_lambda_api_link(arn, function_name, "api", "test",
                                     aws_profile, description=description)
        return url
    else:
        return 'Function deployed successfully'