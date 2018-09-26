#!/usr/bin/env python

import boto3
import json
import os.path

# Bucket directories not designated for synchronization
BLACKLIST_KEYS = [
    "background_pictures",
    "bg_images",
    "collection",
    "cover_images",
    "creatives",
    "creatives_adtemplate_preview_image",
    "facebook_ad_pictures",
    "facebook_products",
    "facebook_products_api",
    "facebook_shareable_images",
    "images",
    "inbound",
    "partners",
    "presale",
    "pro_images",
    "products",
    "profile_images",
    "profile_pictures",
    "promoted_reviews",
    "public",
    "scratch",
    "shops/migrations",
    "signup",
    "template"
]


def check_if_blacklisted(key):
    """ Compare an S3 object's directory name against the blacklist.

    Amazon S3 objects posses keys that mimics an operating system's
    directory structure. Since we have "directories" that we'd like to ignore
    in our synchronizations, we use Python's `os.path` library to evaluate
    object keys as though we're in a filesytem.

    If the top-level directory matches against the blacklist, then skip over it
    when evaluating the copy mechanic.

    Args:
        key: The full S3 object key.

    Returns:
        A tuple designating if the object key is or isn't blacklisted and the
        key that represents the directory that was checked.

    """
    if key in BLACKLIST_KEYS:
        return True, key
    if os.path.dirname(key):
        return check_if_blacklisted(os.path.dirname(key))
    return False, key


def lambda_handler(event, context):
    """ Parse a Lambda trigger, evaluate if S3 object must be copied.

    This function is called upon an S3 object creation event. The payload
    within the `event` contains the source bucket name and the newly created
    object's key.

    The key is passed into a function checking if it's blacklisted. If it is,
    the functinon is returned without an artifact produced. If it isn't, the
    the object is copied to the destination bucket using the payload and the
    target bucket's name.

    This destination bucket's name is derived from the AWS Lambda function's
    name. This is not modified from within this script. It is only managed on
    via the top-level service API. Therefore, each destination bucket has it's
    own Lambda function where the only difference is how they're named on the
    AWS console/API.

    Args:
        event: A dict containing containing event payload data.
        context: The executing Lambda function's runtime information.

    Returns:
        A log message printed to STDOUT designating the object's blacklist
        status and where it was copied.

    """
    s3 = boto3.client('s3')

    sns_message = json.loads(event['Records'][0]['Sns']['Message'])

    # it's important that the lambda function is named exactly like the
    # destination bucket. it's used as the destination bucket placeholder name.
    target_bucket = context.function_name
    source_bucket = sns_message['Records'][0]['s3']['bucket']['name']

    object_key = sns_message['Records'][0]['s3']['object']['key']
    if 's3-assets'in source_bucket:
        msg = "Skipping blacklist check for source bucket: {0}"
        print msg.format(source_bucket)
        pass
    else:
        is_blacklisted, key = check_if_blacklisted(object_key)
        if is_blacklisted:
            print "Blacklisted directory: {0}".format(key)
            return

    # construct the copy operation
    copy_source = {'Bucket': source_bucket, 'Key': object_key}
    msg = "Copying {} from bucket {} to bucket {}"
    print msg.format(object_key, source_bucket, target_bucket)
    s3.copy_object(Bucket=target_bucket, Key=object_key, CopySource=copy_source)
