import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
import docker

from paws.utils import zip_to
from paws.s3 import push_to_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def pull_docker_image(image, tag):
    """
    Pull a docker image with a tag.

    Parameters
    ----------
    image: str
        Image to pull.
    tag: str
        Tag to pull

    Returns
    -------
    True
    """
    logger.info("Pulling new Docker image {} with tag {}".format(image, tag))
    docker_client = docker.from_env()
    docker_client.images.pull(image, tag)
    logger.info("Image pulled")
    return True


def build_layer(requirements, layer_name, layer_dir, overwrite=True):
    """
    Build a .zip file containing a layer for AWS Lambda from a
    requirements file.

    Parameters
    ----------
    requirements: Path or str
        Path or str representation of a path to a pip style
        requirements file.
    layer_name: str
        Name of layer to create. The .zip file created will be in the
        form `layer_name.zip`.
    layer_dir: Path or str
        Directory to save the created layer in. This must already
        exist.
    overwrite: bool, optional
        If any existing layer in the same layer_dir with the same
        layer_name should be overwritten. True by default.

    Returns
    -------
    new_path: Path
        Path to the created .zip of the layer.
    """
    r_path = Path(requirements).absolute()
    logger.info("Requirements file is located at {}".format(r_path))
    to_mount = r_path.parents[0].as_posix()
    logger.info("Mounting directory {}".format(to_mount))

    image = "lambci/lambda"
    tag = "build-python3.6"

    pull_docker_image(image, tag)
    docker_client = docker.from_env()
    commands = ["#!/bin/bash",
                "git config --global http.sslVerify false",
                "pip install -r /u/{} --target /python/".format(r_path.name)]
    command_string = "\n".join(commands)

    logger.info("running command {}".format(command_string))

    with TemporaryDirectory() as t:
        layer_p = Path(t) / layer_name

        command_dir = Path(t) / "commands"
        command_dir.mkdir()
        (command_dir / "command.txt").write_text(command_string)
        command_dir_p = command_dir.absolute().as_posix()

        python_dir = layer_p / "python"

        r = docker_client.containers.run(
            remove=True,
            image="{}:{}".format(image, tag),
            volumes={
                to_mount: {"bind": "/u", "mode": "rw"},
                python_dir: {"bind": "/python", "mode": "rw"},
                command_dir_p: {"bind": "/commands", "mode": "rw"}
            },
            stderr=True,
            stdout=True,
            command="bash /commands/command.txt",
        )
        logger.info("from docker container - {}".format(r))
        new_path = Path(layer_dir) / "{}.zip".format(layer_name)
        logger.info("Sending zipped layer to {}".format(new_path))
        zip_to(layer_p, new_path, overwrite)
    return new_path


def deploy_layer_from_s3_to_lambda(object_key, bucket_name,
                                   aws_profile, layer_name,
                                   description, layer_license):
    """
    Deploy an AWS Lambda layer from an existing S3 object. If the
    layer already exists, its version number will be incremented.

    Parameters
    ----------
    object_key: str
        AWS S3 object key of layer to deploy.
    bucket_name: str
        AWS S3 bucket name containing `object_key`.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    layer_name: str
        Name of layer to create.
    description: str
        Description of layer version.
    layer_license: str
        The layer's software license. It can be any of the following:
            * An SPDX license identifier . For example, `MIT`.
            * The URL of a license hosted on the internet. For example,
            `https://opensource.org/licenses/MIT`.
            * The full text of the license.

    Returns
    -------
    layer_version_arn: str
        LayerVersionArn of the layer.
    """
    os.environ["AWS_PROFILE"] = aws_profile
    lambda_client = boto3.client("lambda")
    r = lambda_client.publish_layer_version(
        LayerName=layer_name,
        Description=description,
        Content={"S3Bucket": bucket_name, "S3Key": object_key},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo=layer_license
    )
    layer_version_arn = r["LayerVersionArn"]
    return layer_version_arn


def deploy_layer(requirements, layer_name, bucket_name, aws_profile,
                 description, layer_license):
    """
    Deploy a layer from a requirements file to AWS Lambda.

    Parameters
    ----------
    requirements: Path or str
        Path or str representation of a path to a pip style
        requirements file.
    layer_name: str
        Name of layer to create.
    bucket_name: str
        Name of bucket to store layer in s3. This must exist.
    aws_profile: str
        Name of profile to use to connect to AWS. This should be
        configured in both `~/.aws/config` and `~/.aws/credentials`.
    description: str
        Description of layer version.
    layer_license: str
        The layer's software license. It can be any of the following:
            * An SPDX license identifier . For example, `MIT`.
            * The URL of a license hosted on the internet. For example,
            `https://opensource.org/licenses/MIT`.
            * The full text of the license.

    Returns
    -------
    layer_version_arn: str
        LayerVersionArn of the layer.
    """
    with TemporaryDirectory() as t:
        layer_path = build_layer(requirements, layer_name, Path(t))
        s3_object = push_to_s3(layer_path, bucket_name, aws_profile)
    r = deploy_layer_from_s3_to_lambda(
        s3_object.key, bucket_name, aws_profile, layer_name,
        description, layer_license
    )
    logger.info("Layer successfully deployed")
    return r


def main():
    s3_bucket_name = "lambda-layers-proagrica"
    requirements_path = Path() / "layer_requirements.txt"
    description = "Data Science modelling layer"
    layer_name = "modelling_layer"
    layer_license = "NO LICENSE"
    aws_profile = "prototype"
    r = deploy_layer(requirements_path, layer_name, s3_bucket_name,
                     aws_profile, description, layer_license)
    return r


if __name__ == "__main__":
    main()
