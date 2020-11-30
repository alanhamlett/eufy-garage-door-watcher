#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import humanize
import json
import pytz
import requests
import smtplib
import sys
import time
from email.message import EmailMessage
from datetime import datetime


from secrets import (
    DELAY_MINUTES,
    EUFY_EMAIL,
    EUFY_PASSWORD,
    TO_EMAILS,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    TIMEZONE,
)


API_BASE: str = "https://mysecurity.eufylife.com/api/v1"
SENSORS_FILE: str = ".sensors.json"
SECRET_FILE: str = ".secret-api-token"


def main() -> int:
    token = get_token()
    if not token:
        error('Missing api token, exiting.')
        return 1
    try:
        resp = requests.post(API_BASE + '/app/get_devs_list', headers={'x-auth-token': token})
        sensors = door_sensors(resp.json()['data'])
    except:
        error(f'Error response from Eufy API devices list {resp.status_code}:\n{resp.text}')
        token = get_token(fresh=True)
        if not token:
            error('Missing api token, exiting.')
            return 1
        try:
            resp = requests.post(API_BASE + '/app/get_devs_list', headers={'x-auth-token': token})
            sensors = door_sensors(resp.json()['data'])
        except:
            error(f'Error response from Eufy API devices list {resp.status_code}:\n{resp.text}')
            return 1

    # Eufy's api sometimes gives stale update_time timestamp, so we make sure
    # it's sane by comparing with the previous sensor state
    try:
        with open(SENSORS_FILE) as fh:
            previous = json.loads(fh.read())
    except:
        previous = []

    for sensor in sensors:
        state = door_sensor_state(sensor)
        updated_at = datetime.utcfromtimestamp(sensor['update_time'])
        prev_state = prev_sensor_state(sensor, previous)
        print(f'{sensor["device_name"]} is {state}.')

        if state == 'open' and open_longer_than_delay(updated_at, prev_state):
            send_email(sensor['device_name'], state, updated_at)

    with open(SENSORS_FILE, 'w') as fh:
        fh.write(json.dumps(sensors))

    return 0


def get_token(fresh: bool = False) -> str:
    if not fresh:
        try:
            with open(SECRET_FILE) as fh:
                token = fh.readline().strip()
                expires_at = fh.readline().split()
                if token and int(expires_at or 0) > int(time.time() + 5):
                    return token
        except:
            pass

    payload = {
        'email': EUFY_EMAIL,
        'password': EUFY_PASSWORD,
    }
    resp = requests.post(API_BASE + '/passport/login', json=payload)
    try:
        token = resp.json()['data']['auth_token']
        expires_at = resp.json()['data']['token_expires_at']
    except:
        error(f'Error response from login to Eufy API {resp.status_code}:\n{resp.text}')
        return ''

    with open(SECRET_FILE, 'w') as fh:
        fh.write(f'{token}\n{expires_at}')

    return token


def door_sensors(devices):
    sensors = []
    for device in devices:
        if device['device_type'] == 2:
            sensors.append(device)
    return sensors


def find_device(devices, sn):
    for device in devices:
        if device['device_sn'] == sn:
            return device
    return None


def door_sensor_state(device) -> str:
    param = next(filter(lambda p: p['param_type'] == 1550, device['params']), None)
    if param is None:
        return 'unknown'
    return 'open' if param['param_value'] == '1' else 'closed'


def prev_sensor_state(sensor, previous_sensors) -> str:
    prev = find_device(previous_sensors, sensor['device_sn'])
    if not prev:
        return None
    return door_sensor_state(prev)


def open_longer_than_delay(updated_at, prev_state) -> bool:
    minutes_open = (datetime.utcnow() - updated_at).total_seconds() / 60
    return minutes_open > DELAY_MINUTES and (minutes_open < DELAY_MINUTES * 2 or prev_state == 'open')


def send_email(device, state, updated_at) -> None:
    duration = humanize.naturaldelta(datetime.utcnow() - updated_at)
    since = format_time(updated_at)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)

    msg = EmailMessage()

    message = f'{device} has been {state} for {duration} since {since}.\n'
    msg.set_content(message)
    msg['Subject'] = f'{device} {state} for {duration}'
    msg['From'] = SMTP_USERNAME
    msg['To'] = ', '.join(TO_EMAILS)
    server.send_message(msg)


def format_time(dt) -> str:
    """Formats datetime like `3pm`."""
    if not dt:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    tz = pytz.timezone(TIMEZONE)
    dt = dt.astimezone(tz)
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


def error(msg: str):
    sys.stderr.write(f'{msg}\n')


if __name__ == '__main__':
    sys.exit(main())
