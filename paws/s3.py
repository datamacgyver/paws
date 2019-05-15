import os
from pathlib import Path

import boto3


def push_to_s3(file, bucket_name, aws_profile, key=None, create_bucket=False,
               location="EU"):
    """
    Push a file to an S3 bucket.

    Parameters
    ----------
    file: Path or str
        Path to the .zip file containing a layer.
    bucket_name: str
        Name of bucket within S3.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    key: str or None, optional
        Key of object within S3. If `None`, the file name will be
        used. None by default.
    create_bucket: bool, optional
        Should the bucket be created if it does not exist? False by
        default.
    location: str
        The location to create the S3 bucket. This is only used if
        `create_bucket` is True.

    Returns
    -------
    r: s3.Object
        s3.Object of the layer.
    """
    os.environ["AWS_PROFILE"] = aws_profile
    s3_client = boto3.resource("s3")

    file_path = Path(file)
    file_content = file_path.read_bytes()

    bucket = s3_client.Bucket(name=bucket_name)
    if key is None:
        key = file_path.name

    try:
        r = bucket.put_object(ACL="private", Body=file_content,
                              Key=file_path.name)
    except boto3.client("s3").exceptions.NoSuchBucket as e:
        if create_bucket:
            bucket.create(CreateBucketConfiguration={
                'LocationConstraint': location})
            r = bucket.put_object(ACL="private", Body=file_content,
                                  Key=key)
        else:
            raise e
    return r


def get_from_s3(bucket_name, key, aws_profile=None):
    """
    Get a file to an S3 bucket.

    Parameters
    ----------
    bucket_name: str
        Name of bucket within S3.
    key: str
        Key of object within S3 (name of file).
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.

    Returns
    -------
    data:
        content of the file.
    """
    if aws_profile:
        os.environ["AWS_PROFILE"] = aws_profile
    s3_client = boto3.client("s3")

    file_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
    data = file_obj["Body"]

    return data
