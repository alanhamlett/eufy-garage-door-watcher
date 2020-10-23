#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import humanize
import requests
import pytz
import smtplib
from email.message import EmailMessage
from datetime import datetime


from secrets import (
    EUFY_EMAIL,
    EUFY_PASSWORD,
    TO_EMAILS,
    SMTP_USERNAME,
    SMTP_PASSWORD,
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
    updated_at = datetime.utcfromtimestamp(device['update_time'])
    print(f'{device["device_name"]} is {status}.')

    if status == 'open':
        send_email(device['device_name'], status, updated_at)


def first_door_sensor(devices):
    for device in devices:
        if device['device_type'] == 2:
            return device
    return None


def send_email(device, status, updated_at) -> None:
    duration = humanize.naturaldelta(datetime.utcnow() - updated_at)
    since = format_time(updated_at)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)

    msg = EmailMessage()

    message = f'{device} has been {status} for {duration} since {since}.\n'
    msg.set_content(message)
    msg['Subject'] = f'{device} {status} for {duration}'
    msg['From'] = SMTP_USERNAME
    msg['To'] = ', '.join(TO_EMAILS)
    server.send_message(msg)


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


if __name__ == '__main__':
    main()
