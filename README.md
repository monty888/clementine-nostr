# clementine-nostr
status updates for nostr from clementine music player

# install

```sh
git clone https://github.com/monty888/clementine-nostr.git
cd clementine-nostr  
python3 -m venv venv   
source venv/bin/activate   
pip install -r requirements.txt
```

# running

In Clementine enable network remote - Preferences/Network Remote. 

Run as below either, config options are either taken from toml file currently
hardcoded to be at USER/.nostrpy/nostr_track.toml (example included) or from the command line.

```sh
python nostr_track.py
```

```commandline
python nostr_track.py --help
usage: nostr_track.py [-h] [-r RELAY] [-u USER] [-i CLEMENTINE_IP] [-p CLEMENTINE_PORT] [-a CLEMENTINE_AUTH] [-d]

update nostr status with currently playing track from Clementine music player

options:
  -h, --help            show this help message and exit
  -r RELAY, --relay RELAY
                        comma separated nostr relays to connect to, default[wss://nostr-
                        pub.wellorder.net,wss://nos.lol,wss://relay.nostr.band]
  -u USER, --user USER  alias or nsec of user we're going to publish status updates as default[monty]
  -i CLEMENTINE_IP, --ip CLEMENTINE_IP
                        ip used to connect to clementine, default[192.168.0.30]
  -p CLEMENTINE_PORT, --port CLEMENTINE_PORT
                        port used to connect to clementine, default[5500]
  -a CLEMENTINE_AUTH, --auth CLEMENTINE_AUTH
                        auth code used to connect to clementine, default[12654]
  -d, --debug           enable debug output
```