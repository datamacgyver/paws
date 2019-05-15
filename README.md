# paws
**Alpha release**

paws - Proagrica Amazon Web Services. Tools to make using AWS easier. At 
present this is largely Lambda deployment tools. Other stuff to be added. 

# Lambda function deployment

## Layers

[Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
are the new kid on the block for AWS Lambda. They allow you to build runtime 
environments and ship packages which can be shared across multiple functions. 
More importantly, they allow you to get around the size limit for a lambda 
function. 

Layers are versioned and can be viewed in the layers subtab of the lambda 
section of the AWS console.

### Creating a Layer

Creating a layer can be awkward. It isn't as simple as zipping up a package 
that you have installed on your local machine, as the code must be correctly 
configured for the lambda environment.

**Enter Docker**

Docker allows us to create a lambda-like runtime, within which we can install 
packages and create a layer. In this example this is done using the lambda 
images available at [lambci/lambda](https://hub.docker.com/r/lambci/lambda/). 
To create a layer, we run a container, mapping a volume from the local machine 
into which we will install the relevant packages.

This sounds complicated right?

In `paws.lambda_tools.layer_tools` there exists a function which will 
build a layer given a requirements file, `build_layer()`. This makes life much 
easier. 

### Deploying a Layer

Deploying a layer is fairly easy. It can be done through the console or 
through the api. However, the api has a size limit which is not reflected 
through other means. To get around this, it is possible to deploy a layer 
from S3. This means we first publish the layer to an S3 object, and then 
deploy this as a layer in Lambda. Again, functions exist in `paws.s3` 
and `paws.lambda_tools.layer_tools` to do both these things.

### All In One

The above steps are fairly simple. However, they are multiple steps which can 
easily be combined and automated. To do this, there is a function 
`paws.lambda_tools.layer_tools.deploy_layer()` which will do all of 
this. To run it with preset inputs, you can use 
`paws.lambda_tools.layer_tools.deploy.main()`.

## Lambda Functions

Lambda functions are hard, fussy and tempremental. And deploying them brings 
all of these issues to the fore. Once you try and integrate them into the 
APIGateway, things get even messier. Helper functions have been written to 
help this process go as smoothly as possible. These are broken into 3 stages.

### Writing a Lambda Function

On creation, a Lambda function should have a handler defined. This is the 
`module.function` which will be called on invocation. Traditionally, this 
function is given two inputs, `event` and `context`. `Event` contains the 
input data, `context` metadata about the function and the call. 

The event input is typically a dict of inputs. APIGateway does not do this. 
When the APIGateway is used to invoke a Lambda function, it gives a huge json 
with lots of fluff in it, and the inputs are contained within a `body` 
attribute, as a string. This makes testing and development difficult, and 
means functions cannot be tested as standalone functions and then as Lambda 
functions.

To help overcome this, a decorator has been written. This decorator lives at
`paws.lambda_tools.decorators` and, therefore, has to be shipped as
a layer, following the instructions above. Using this decorator, the handler 
should accept a `**kwargs` input and define its parameters internally. It 
should then perform its logic and simply return something which can be 
serialisable. The decorator will ensure that a well formed json is returned, 
the output of the function is serialised, and if an error occurs a status of 
500 will be returned with the message `An Error Occurred.`.

#### Directory Structure

The lambda function should be in its own directory. The file should be named 
`lambda_function.py`, since it is the default of 
`paws.lambda_tools.function_tools.create_function`, which is called
within `paws.lambda_tools.function_tools.deploy_function()`.
This should be something like:

```
.
├── ...
├── requirements.txt (optional)
├── my_custom_lambda_function
|   ├── __init__.py
|   └── lambda_function.py
└── ...
```

#### Example

**Lambda function**

```python
import logging

import pandas as pd

from paws.lambda_tools.decorators import lambda_api

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

@lambda_api
def lambda_handler(**kwargs):
    num = kwargs.get("num", 3)
    exc = kwargs.get("exc", "!")
    result = pd.Series(["hello world{}".format(exc)] * num).to_json()
    return result
```

**Layer requirements**

```
pandas==0.23.4
git+https://gitlab.agb.rbxd.ds/DataScience/paws/
```

#### Testing

The function `lambda_handler` can also now be tested by itself, using:
```python
input_dict = {"num": 7, "exc": "!!"}
lambda_handler(**input_dict)
```

### Deploying a Lambda Function

Creating, deploying and integrating a Lambda function with the APIGateway can 
be fussy. Updates can also be awkward. To make this easier, there are two 
functions (which call many more, very useful, underlying functions) in 
`paws.lambda_tools.function_tools`. 

#### Deploy Function

`paws.lambda_tools.function_tools.deploy_function()` allows us to 
quickly create a new lambda function with a functioning api. Its inputs are 
the Lambda function name, the path of the function 
(`.//my_custom_lambda_function` in the above example), the S3 bucket in which 
to store the zipped function, the AWS profile used to connect to AWS, and 
layers you want to associate to the function, and the description of the 
function.

It returns the url of the newly created api which can be used to access the 
function.

#### Testing

To test this using the Lambda functions testing in the console, the test json 
should be:

```javascript
{
  "body": "{\"num\": 7, \"exc\": \"!!\"}"
}
```

To test this using the APIGateway:
```python
requests.post(url, json={"num": 7, "exc": "!!"}).json()
```

#### Update Function

`paws.lambda_tools.function_tools.update_function()` allows us to 
update a function. It does just a bit less than the above.