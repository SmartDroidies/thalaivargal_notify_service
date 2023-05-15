import decimal
import json
import math
import time
from datetime import datetime, timedelta


def current_timestamp():
    return math.trunc(time.mktime(datetime.now().timetuple()))


def datetime_timestamp(date_time):
    return math.trunc(time.mktime(date_time.timetuple()))


def get_epochtime_ms():
    return round(datetime.utcnow().timestamp() * 1000)


def extract_error(err):
    if err.message:
        return err.message
    else:
        return err


def respond(err, res=None):
    print(err)
    return {
        'statusCode': '400' if err else '200',
        'body': extract_error(err) if err else json.dumps(res, cls=DecimalEncoder),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def validate(date_text):
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")


def increment_day(date_text):
    return (datetime.strptime(date_text, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')


def ninty_days_back():
    return (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')


def current_date():
    return datetime.now().strftime('%Y-%m-%d')
