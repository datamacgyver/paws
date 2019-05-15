import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def lambda_api(f):
    base = {
        'headers': {
            'Content-Type': 'application/json',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True
        },
    }

    def wrapper(*args):
        logger.debug("inputs are: {}".format(args))
        try:
            input_body = args[0]["body"]
            logger.debug("calling function with {}".format(input_body))
            if input_body:
                x = json.loads(input_body)
                body = f(**x)
            else:
                logger.info("No body present")
                body = f()
            body = json.dumps(body)
        except Exception as e:
            base["statusCode"] = 500
            base["body"] = "An Error Occurred"
            logger.exception(e)
        else:
            base["body"] = body
            base["statusCode"] = 200
        finally:
            logger.debug("returning {}".format(base))
            return base
    return wrapper
