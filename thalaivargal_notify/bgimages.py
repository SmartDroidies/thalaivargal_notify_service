import json
import os

import boto3
import common

# For Testing
# os.environ['IMAGE_WEBSITE'] = "http://www.smartdroidies.com/"
IMG_WEBSITE = os.environ['IMAGE_WEBSITE']


def create_bg_image(category, item):
    bg_image = {'code': category, 'url': IMG_WEBSITE + item.key,
                'modified': common.datetime_timestamp(item.last_modified)}
    return bg_image


def collect_bgimages_bycode(category):
    bg_images = []
    s3 = boto3.resource('s3')
    bucket_images = s3.Bucket('smartdroidies.com')
    prefix = 'tamil-quotes-bg/' + category
    for item in bucket_images.objects.filter(Prefix=prefix):
        if item.key[-1] != '/':
            bg_images.append(create_bg_image(category, item))
    return bg_images


def collect_bgcolors():
    s3 = boto3.client('s3')
    bgcolorsobj = s3.get_object(Bucket="tamil-quotes", Key="colors.json")
    bgimagesjson = json.loads(bgcolorsobj['Body'].read())
    return bgimagesjson


def collect_text_colors():
    s3 = boto3.client('s3')
    text_colors_obj = s3.get_object(Bucket="tamil-quotes", Key="text-colors.json")
    text_colors_json = json.loads(text_colors_obj['Body'].read())
    return text_colors_json


def image_handler(event, context):
    if event['queryStringParameters'] and "code" in event['queryStringParameters']:
        if event['queryStringParameters']['code'] == 'color':
            return common.respond(None, collect_bgcolors())
        elif event['queryStringParameters']['code'] == 'text-color':
            return common.respond(None, collect_text_colors())
        else:
            category = event['queryStringParameters']['code']
            return common.respond(None, collect_bgimages_bycode(category))
    else:
        s3 = boto3.client('s3')
        bgimagesobj = s3.get_object(Bucket="tamil-quotes", Key="bgimages.json")
        bgimagesjson = json.loads(bgimagesobj['Body'].read())
        return common.respond(None, bgimagesjson)
