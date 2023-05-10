import json


def is_authorized():
    return True


# Invoke:sam local invoke --event events/authorize_event.json CourseAuthFunction
def handler(event, context):
    print("Received auth event: " + json.dumps(event, indent=5))
    print("Client token: " + event['authorizationToken'])
    print("Method ARN: " + event['methodArn'])

    response = {
        "isAuthorized": 'false',
        "context": {
            "stringKey": "dummy",
        }
    }

    if is_authorized():
        response = {
            "isAuthorized": 'true',
            "context": {
                "stringKey": "dummy",
            }

        }

    return response