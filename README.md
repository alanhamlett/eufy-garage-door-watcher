# Eufy Garage Door Watcher

Send yourself an email whenever the garage door is left open, using a [Eufy Security door sensor][sensor].

![email notification example](/example.png?raw=true)

## Installation

    git clone https://github.com/alanhamlett/eufy-garage-door-watcher.git && cd eufy-garage-door-watcher
    pip3 install -r requirements.txt
    cp secrets.py.example secrets.py
    echo "*/5 * * * * root $PWD/watch_garage_door.py" > /etc/cron.d/eufy-garage-door-watcher

Make sure to edit `secrets.py` with your [Eufy Guest account][guest account] and [Gmail App Password][gmail].

[sensor]: https://www.eufylife.com/products/variant/entry-sensor/T89000D4
[guest account]: https://communitysecurity.eufylife.com/t/adding-family-guest/101321/8
[gmail]: https://myaccount.google.com/apppasswords
