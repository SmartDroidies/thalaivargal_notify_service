import decimal
import json

import boto3
import common
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('userquote')


def getLatestSync(input):
    if 'latestsync' in input:
        return decimal.Decimal(input['since'])
    else:
        return 0


def create_user_quote(quote):
    current_ts = common.current_timestamp()
    quote["id"] = current_ts
    quote["modified"] = current_ts
    print(json.dumps(quote, indent=2))
    return quote


def store_user_quote(user_quote):
    quote_obj = create_user_quote(user_quote)
    # FIXME - Uniqueness on notify date attribute_not_exists
    response = table.put_item(Item=quote_obj,
                              ConditionExpression='attribute_not_exists(weight)')
    # print(response)
    return quote_obj


def read_user_quote_id(quoteid):
    response = table.query(
        KeyConditionExpression=Key('id').eq(decimal.Decimal(quoteid))
    )
    items = response['Items']
    if items:
        return items[0]
    else:
        return None


def read_user_quote_count(code):
    response = table.scan(
        FilterExpression=Attr('code').eq(code)
    )
    items = response['Items']
    return items


def read_user_quote_code(code, latestsync):
    response = table.scan(
        FilterExpression=Attr('code').eq(code) & Attr('modified').gt(latestsync)
    )
    items = response['Items']
    return items


def read_user_quote_leader(leader, latestsync):
    response = table.scan(
        FilterExpression=Attr('leader').eq(leader) & Attr('modified').gt(latestsync)
    )
    items = response['Items']
    return items


def search_user_quote(searchField, searchTerm):
    # FIXME - Handle search field
    response = table.scan(
        FilterExpression=Attr('desc').contains(searchTerm)
    )
    items = response['Items']
    return items


def read_user_quote(input_param):
    if "id" in input_param:
        return read_user_quote_id(input_param['id'])
    elif "code" in input_param:
        return read_user_quote_code(input_param['code'], getLatestSync(input_param))
    elif "leader" in input_param:
        return read_user_quote_leader(input_param['leader'], getLatestSync(input_param))
    elif "search" in input_param:
        return search_user_quote(input_param['search'], input_param['term'])
    # elif "daily" in input_quote:
    #     return read_daily_quote(input_quote['daily'])
    # elif "notify_date" in input_quote:
    #     return read_notify_quote(input_quote['notify_date'])
    else:
        return "No filter parameter passed"


def delete_user_quote(input_param):
    return table.delete_item(Key={'id': input_param['id']})


def update_user_quote(user_quote):
    db_quote = read_user_quote_id(user_quote["id"])
    if db_quote is not None:
        user_quote["modified"] = common.current_timestamp()
        response = table.put_item(Item=user_quote)
        print(response)
        return user_quote
    else:
        return None


def patch_user_quote(user_quote_positions):
    # print(type(user_quote_positions))
    for user_quote_position in user_quote_positions:
        update_expression = 'SET weight = :weight, modified = :modified'
        expression_attribute_values = {
            ':weight': user_quote_position['weight'],
            ':modified': common.current_timestamp()
        }

        table.update_item(
            Key={'id': user_quote_position['id']},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
    return None


def collect_latest_quote_bycode(code):
    scan_args = {
        'FilterExpression': Attr('code').eq(code),
        'ProjectionExpression': "id, author, code, bg, modified"
    }

    done = False
    start_key = None
    counter = 0
    while not done:
        if start_key:
            scan_args['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_args)
        list_quotes = response.get('Items', [])
        list_quotes.sort(key=lambda x: x['modified'], reverse=True)
        # print("Reverse Sorted :  " + str(list_quotes[0]['id']))
        return list_quotes


def user_quote_handler(event, context):
    # print("Received event for User Quote: " + json.dumps(event, indent=2))

    operations = {
        'POST': lambda x: store_user_quote(x),
        'GET': lambda x: read_user_quote(x),
        'DELETE': lambda x: delete_user_quote(x),
        'PUT': lambda x: update_user_quote(x),
        'PATCH': lambda x: patch_user_quote(x),
    }

    operation = event['httpMethod']
    if operation in operations:
        payload = event['queryStringParameters'] if operation == 'GET' else json.loads(event['body'])
        return common.respond(None, operations[operation](payload))
    else:
        return common.respond(ValueError('Unsupported method "{}"'.format(operation)))
