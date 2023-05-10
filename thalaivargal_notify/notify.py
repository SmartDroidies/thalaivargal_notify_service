import json
import os
import random
from datetime import datetime, timedelta

import bgimages
import boto3
import common
import firebase_admin
import userquote
from boto3.dynamodb.conditions import Attr, Key
from firebase_admin import messaging

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firebase-adminsdk.json"
firebase_admin.initialize_app()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('notify')
table_event = dynamodb.Table('events')


def create_notify(when, timing, code, quote_id, bg):
    current_ts = common.current_timestamp()
    notify = {"id": when + "-" + timing, "when": when, "timing": timing, "code": code, "quoteid": quote_id,
              "modified": current_ts}
    if (bg):
        notify['bg'] = bg
    # print(json.dumps(notify, indent=2, cls=DecimalEncoder))
    return notify


def notify_quote_param(input_params):
    print("Received parameters: " + json.dumps(input_params, indent=2))
    if "token" in input_params and "quote_id" in input_params:
        return send_notification_quote(input_params['token'], input_params['quote_id'])
    if "topic" in input_params:
        return send_topic_notification(input_params['topic'], input_params)
    else:
        return read_notify_schedule(input_params)


def extract_randon_quote(latestquotes, scheduled_quotes):
    flag_keep_searching = True
    while flag_keep_searching and len(latestquotes) > 0:
        quote = latestquotes.pop(0)
        if quote['id'] not in scheduled_quotes and len(scheduled_quotes):
            # print("Found a new quote ", quote['id'])
            flag_keep_searching = False
    return quote


def extract_randon_bgimage(images):
    if images:
        bgimage = random.choice(images)
        if bgimage and 'url' in bgimage:
            return bgimage['url']
        else:
            return None
    else:
        return None


def append_timing_items(list_notify, response, scheduled_quotes, timing, code, active_date, days):
    latestquotes = userquote.collect_latest_quote_bycode(code)
    images = bgimages.collect_bgimages_bycode(code)
    counter = 0
    if latestquotes:
        for index in range(days):
            if latestquotes:
                random_quote = extract_randon_quote(latestquotes, scheduled_quotes)
                bg = random_quote['bg'] if 'bg' in random_quote else extract_randon_bgimage(images)
                list_notify.append(create_notify(active_date, timing, code, random_quote['id'], bg))
                active_date = common.increment_day(active_date)
                counter = counter + 1
    response.append({"code": code, "timing": timing, "scheduled": counter})


def collect_recent_scheduled():
    ninty_day_back = common.ninty_days_back()
    # print("90 days back : " + ninty_day_back)
    response = table.scan(
        FilterExpression=Attr('when').gt(ninty_day_back),
        ProjectionExpression="quoteid"
    )
    items = response['Items']
    ids = []
    for sub in items:
        ids.append(sub['quoteid'])
    # print(ids)
    return ids


def prepare_daily_notification(input):
    # print("Input: " + json.dumps(input, indent=2))
    list_notify = []
    respone = []
    active_date = input["start"]
    common.validate(active_date)
    days = input["days"] if "days" in input else 7
    dict_category = input['category']
    scheduled_quotes = collect_recent_scheduled()
    for key in dict_category:
        # print(key, '->', dict_category[key])
        append_timing_items(list_notify, respone, scheduled_quotes, key, dict_category[key], active_date, days)
    for item in list_notify:
        table.put_item(Item=item)
    # print("Insert notify : " + json.dumps(item, indent=2, cls=DecimalEncoder))
    return respone


def read_notify_schedule(params):
    if "id" in params:
        response = table.query(
            KeyConditionExpression=Key('id').eq(params['id'])
        )
        if response['Items']:
            return response['Items'][0]
        else:
            return None
    else:
        yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        response = table.scan(
            FilterExpression=Attr('when').gte(yesterday)
        )
        items = response['Items']
        return items


def send_notification_quote(registration_token, quote_id):
    notifyquote = userquote.read_user_quote_id(quote_id)
    notification = messaging.Notification(
        body=notifyquote['desc']
    )
    return trigger_token_notification(registration_token, notification, quote_id)


def trigger_warn_notification(title, body):
    print("Send warn notification")
    notification = messaging.Notification(
        body=body,
        title=title
    )
    data = {"desc": body}
    return trigger_topic_notification("develop", notification, data)


def read_event(notify_date):
    response = table_event.scan(
        FilterExpression=Attr('event_date').eq(notify_date)
    )
    items = response['Items']
    if items:
        return items[0]
    else:
        return None


def send_topic_notification(topic, params):
    if "title" in params and "body" in params:
        notification = messaging.Notification(
            body=params['body'],
            title=params['title']
        )
        data = {"ts": str(common.current_timestamp())}
        if "code" in params:
            data['code'] = params['code']
        return trigger_topic_notification(topic, notification, data)
    elif "timing" in params:
        notify_date = params["notify_date"] if "notify_date" in params else datetime.today().strftime('%Y-%m-%d')
        quotes = read_notify_quote(notify_date, params['timing'])
        if quotes:
            quote = userquote.read_user_quote_id(quotes[0]['quoteid'])
            if quote:
                # print('Send notification for quote : ' + str(quotes[0]['quoteid']))
                notification = messaging.Notification(
                    body=quote['desc'],
                    title="இன்றய பொன்மொழி"
                )
                data = {"ts": str(common.current_timestamp()), "quote_id": str(quote['id']), "code": quote['code']}
                if "bg" in quotes[0]:
                    data["bg"] = quotes[0]["bg"]
                print("Push Data : ", data)
                return trigger_topic_notification(topic, notification, data)
            else:
                print('Notification Quote missing send alert to developer device')
                return trigger_warn_notification("Warn",
                                                 "Missing scheduled daily quote : " + notify_date + " - " + quote['id'])
        else:
            print('Notification missing send alert to developer device')
            return trigger_warn_notification("Warn", "Missing daily quote schedule : " + notify_date)
    elif "event" in params:
        notify_date = params["notify_date"] if "notify_date" in params else datetime.today().strftime('%Y-%m-%d')
        event = params["event"]
        if event == "tomorrow":
            notify_date = common.increment_day(notify_date)
        alert_event = read_event(notify_date)
        if alert_event:
            image = alert_event["image"] if "image" in alert_event else None
            print("Send notification for : " + alert_event['event_title'])
            notification = messaging.Notification(
                title=alert_event['event_title'],
                body=alert_event['desc'],
                image=image
            )
            data = {"ts": str(common.current_timestamp()), "type": "event", "id": alert_event['id']}
            if "code" in alert_event:
                data['code'] = alert_event['code']
            elif "tags" in alert_event:
                data['code'] = alert_event['tags'].split(",")[1]
            return trigger_topic_notification(topic, notification, data)
        else:
            return trigger_warn_notification("Info",
                                             "Missing event quote for : " + params['event'] + " - " + notify_date)
    else:
        return "Request params not supported"


def send_daily_notification(target_date):
    # quote = read_notify_quote(target_date)
    # if quote is not None:
    #     notification = messaging.Notification(
    #         title=quote['notify'],
    #         body='Daily Quote',
    #     )
    #     return trigger_topic_notification(notify_config.notify_token, notification, target_date)
    # else:
    #     notification = messaging.Notification(
    #         title='Critical Alert',
    #         body='Quote not found for : ' + target_date,
    #     )
    #     # print ("Send Notification : " + notification.body)
    #     return trigger_token_notification(notify_config.admin_token, notification, target_date)
    return "Not implemented"


def read_notify_quote(notify_date, timing):
    response = table.scan(
        FilterExpression=Attr('when').eq(notify_date) & Attr('timing').eq(timing)
    )
    items = response['Items']
    return items


def trigger_token_notification(registration_token, notification, quote_id):
    message = messaging.Message(
        notification=notification,
        data={"quote_id": quote_id},
        token=registration_token,
    )
    response = messaging.send(message)
    return 'Successfully sent message:', response


def trigger_topic_notification(topic, notification, data):
    # print(data)
    message = messaging.Message(
        notification=notification,
        data=data,
        topic=topic
    )
    response = messaging.send(message)
    return 'Successfully sent message to topic:', response


def notify_handler(event, context):
    # print("Received notify event: " + json.dumps(event, indent=2))
    operations = {
        'GET': lambda x: notify_quote_param(x),
        'POST': lambda x: prepare_daily_notification(x)
    }

    operation = event['httpMethod']
    # print('\nOperation :  ' + operation)
    if operation in operations:
        payload = event['queryStringParameters'] if operation == 'GET' else json.loads(event['body'])
        return common.respond(None, operations[operation](payload))
    else:
        return common.respond(ValueError('Unsupported method "{}"'.format(operation)))


def notify_schedule_handler(event, context):
    # print("Received notify event: " + json.dumps(event, indent=2))
    result = notify_quote_param(event)
    print(result)
    return result
