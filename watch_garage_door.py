#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import pytz
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta


from secrets import (
    EUFY_EMAIL,
    EUFY_PASSWORD,
    EMAIL,
    PASSWORD,
)


TIMEZONE = pytz.timezone('America/Los_Angeles')
API_BASE: str = "https://mysecurity.eufylife.com/api/v1"
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587


def main() -> None:
    payload = {
        'email': EUFY_EMAIL,
        'password': EUFY_PASSWORD,
    }
    resp = requests.post(API_BASE + '/passport/login', json=payload)
    data = resp.json()['data']
    token = data['auth_token']
    # expires = datetime.fromtimestamp(data['token_expires_at'])
    # domain = data.get('domain')

    resp = requests.post(API_BASE + '/app/get_devs_list', headers={'x-auth-token': token})
    device = first_door_sensor(resp.json()['data'])
    param = next(filter(lambda p: p['param_type'] == 1550, device['params']), None)
    status = 'open' if param['param_value'] == "1" else 'closed'
    updated_at = datetime.utcfromtimestamp(param['update_time'])
    print(f'{device["device_name"]} is {status}.')

    if status == 'open':
        send_email(device['device_name'], status, updated_at)


def first_door_sensor(devices):
    for device in devices:
        if device['device_type'] == 2:
            return device
    return None


def send_email(device, status, updated_at) -> None:
    duration = natural_time(updated_at)
    since = format_time(updated_at)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(EMAIL, PASSWORD)

    msg = EmailMessage()

    message = f'{device} has been {status} for {duration} since {since}.\n'
    msg.set_content(message)
    msg['Subject'] = f'{device} {status} for {duration}'
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    server.send_message(msg)


def natural_time(dt, timezone=None, show_tense=False, allow_future=True, short=False) -> str:
    """Returns given timestamp/datetime as string like '2 hours ago'."""

    if dt is None:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    dt = dt.astimezone(TIMEZONE)
    today = TIMEZONE.normalize(
        datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(TIMEZONE)
    )
    in_future = dt > today
    delta = abs(today - dt)
    scale = largest_scale_for_delta(delta)

    if scale == 'second':
        value = delta.total_seconds()
    elif scale == 'minute':
        value = delta.total_seconds() // 60
    elif scale == 'hour':
        value = delta.total_seconds() // 60 // 60
    elif scale == 'day':
        value = delta.total_seconds() // 60 // 60 // 24
    elif scale == 'week':
        value = delta.total_seconds() // 60 // 60 // 24 // 7
    elif scale == 'month':
        value = delta.total_seconds() // 60 // 60 // 24 / 30.42
    elif scale == 'year':
        value = delta.total_seconds() // 60 // 60 // 24 // 365

    value = int(value)
    if value == 0:
        value = 1

    tense = 'ago'
    if in_future and allow_future:
        tense = 'in the future'

    plural = 's'
    if value == 1:
        plural = ''

    return '{value} {scale}{plural}{tense}'.format(
        value=value,
        scale=trim_scale(scale) if short else scale,
        plural=plural,
        tense=' ' + tense if show_tense else '',
    )


def format_time(dt) -> str:
    """Formats datetime like `3pm`."""
    if not dt:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    dt = dt.astimezone(TIMEZONE)
    hour = dt.strftime('%H')
    minute = dt.strftime('%M')
    if hour == '00':
        return dt.strftime('12{minute}am').format(
            minute=':' + minute if minute != '00' else '',
        )
    hour = int(hour.lstrip('0'))
    if hour > 12:
        hour -= 12
    return dt.strftime('{hour}{minute}{ampm}').format(
        hour=hour,
        minute=':' + minute if minute != '00' else '',
        ampm=dt.strftime('%p').lower(),
    )


def largest_scale_for_delta(delta) -> str:
    delta = abs(delta)
    if delta < timedelta(minutes=1):
        return 'second'
    if delta < timedelta(hours=1):
        return 'minute'
    if delta < timedelta(days=1):
        return 'hour'
    if delta < timedelta(days=7):
        return 'day'
    if delta < timedelta(days=31):
        return 'week'
    if delta < timedelta(days=365):
        return 'month'
    return 'year'


def trim_scale(scale) -> str:
    if scale == 'second':
        return 'sec'
    if scale == 'minute':
        return 'min'
    if scale == 'hour':
        return 'hr'
    if scale == 'day':
        return 'day'
    if scale == 'week':
        return 'wk'
    if scale == 'month':
        return 'mon'
    return 'yr'


if __name__ == '__main__':
    main()
