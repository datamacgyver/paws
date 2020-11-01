import os
import boto3


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

