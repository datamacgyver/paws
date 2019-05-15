from setuptools import setup, find_packages

setup(
    name='paws',
    version='0.0.1',
    description='AWS Tools for the proagrica data science team.',
    author='Jack Cooper',
    author_email='jack.cooper@reedbusiness.com',
    license='GNU GPLv3',
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        "boto3",
        'docker'
    ]
)
