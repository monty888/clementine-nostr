import logging
import asyncio
import time
from pathlib import Path
import toml
from toml import TomlDecodeError
import os
import argparse
import signal
import sys
from clementineremote import ClementineRemote
from monstr.event.event import Event
from monstr.ident.alias import ProfileFileAlias
from monstr.client.client import ClientPool
from monstr.util import ConfigError
from monstr.encrypt import Keys

# defaults
WORK_DIR = f'{Path.home()}/.nostrpy/'
# toml config file
CONFIG_FILE = 'nostr_track.toml'
# alias file
ALIAS_FILE = f'{WORK_DIR}profiles.csv'
# default relays
RELAYS = 'ws://localhost:8081'
# to attach to clementine - remote must be enabled
CLEMENTINE_IP = None
CLEMENTINE_PORT = 5500
CLEMENTINE_AUTH = None


def load_toml(filename, dir):
    if os.path.sep not in filename:
        filename = dir+os.path.sep+filename

    ret = {}
    f = Path(filename)
    if f.is_file():
        try:
            ret = toml.load(filename)
        except TomlDecodeError as te:
            raise ConfigError(f'Error in config file {filename} - {te} ')
    else:
        logging.debug(f'load_toml:: no config file {filename}')
    return ret


def get_cmdline_args(args) -> dict:
    parser = argparse.ArgumentParser(
        prog='nostr_track.py',
        description="""
            update nostr status with currently playing track from Clementine music player 
            """
    )
    # TODO: add these in as options
    # parser.add_argument('-c', '--conf', action='store', default=args['conf'],
    #                     help=f'name com TOML file to use for configuration, default[{args["conf"]}]')
    # parser.add_argument('--work-dir', action='store', default=args['work-dir'],
    #                     help=f'base dir for files used if full path isn\'t given, default[{args["work-dir"]}]')
    parser.add_argument('-r', '--relay', action='store', default=args['relays'],
                        help=f'comma separated nostr relays to connect to, default[{args["relays"]}]')
    parser.add_argument('-u', '--user', action='store', default=args['user'],
                        help=f"""
                        alias or nsec of user we're going to publish status updates as
                        default[{args['user']}]""")

    # to attach clementine
    parser.add_argument('-i', '--ip', action='store', default=args['clementine_ip'],
                        help=f'ip used to connect to clementine, default[{args["clementine_ip"]}]',
                        dest='clementine_ip')
    parser.add_argument('-p', '--port', action='store', default=args['clementine_port'],
                        help=f'port used to connect to clementine, default[{args["clementine_port"]}]',
                        dest='clementine_port')
    parser.add_argument('-a', '--auth', action='store', default=args['clementine_auth'],
                        help=f'auth code used to connect to clementine, default[{args["clementine_auth"]}]',
                        dest='clementine_auth')

    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output', default=args['debug'])

    ret = parser.parse_args()

    return vars(ret)

def get_config_int(name, val):
    try:
        return int(val)
    except ValueError as ve:
        raise ConfigError(f'{name} in value is required received {val}')


def get_config() -> dict:
    # defaults if not otherwise give
    ret = {
        'relays': RELAYS,
        'user': None,
        'clementine_ip': CLEMENTINE_IP,
        'clementine_port': CLEMENTINE_PORT,
        'clementine_auth': CLEMENTINE_AUTH,
        'debug': False
    }

    # override from toml
    ret.update(load_toml(filename=CONFIG_FILE,
                         dir=WORK_DIR))

    # final override from cmd line
    ret.update(get_cmdline_args(ret))

    # set logger to debug if debug is True
    if ret['debug']:
        logging.getLogger().setLevel(logging.DEBUG)

    # do some checks on what we have
    if ret['clementine_ip'] is None:
        raise ConfigError('clementine_ip is required')

    if ret['user'] is None:
        raise ConfigError('user needs to be set either with nsec or alias')
    else:
        # try to turn user into keys we can use
        user = ret['user']
        keys = Keys.get_key(user)
        if keys is None:
            # see if we're using alias
            my_alias = ProfileFileAlias(ALIAS_FILE)
            profile = my_alias.get_profile('monty')
            if user:
                keys = profile.keys

        # at this point if we don't have keys or we have keys but not with private key we're done
        if keys is None or keys.private_key_hex() is None:
            raise ConfigError('bad keys or alias - require nsec or alias with private key')

    if ret['clementine_auth'] is not None:
        ret['clementine_auth'] = get_config_int('clementine_auth', ret['clementine_auth'])
    if ret['clementine_port'] is not None:
        ret['clementine_port'] = get_config_int('clementine_port', ret['clementine_port'])

    logging.debug(f'starting with config - {ret}')
    return ret


async def watch_tracks(args):
    last_title = None

    # extract vals from args
    relays = args['relays'].split(',')
    clementine_ip = args['clementine_ip']
    clementine_port = args['clementine_port']
    clementine_auth = args['clementine_auth']

    my_alias = ProfileFileAlias(ALIAS_FILE)

    user = my_alias.get_profile('monty')

    # create and start nostr client pool
    client = ClientPool(clients=relays)
    asyncio.create_task(client.run())

    # link to clementime
    clementine = ClementineRemote(auth_code=clementine_auth,
                                  host=clementine_ip,
                                  port=clementine_port)


    run = True

    def sigint_handler(signal, frame):
        nonlocal run
        run = False

    signal.signal(signal.SIGINT, sigint_handler)

    while run:
        c_track = clementine.current_track

        if clementine.state == 'Playing' and c_track:
            if last_title is None or c_track["title"] != last_title:

                status_content = f'{c_track["track"]} {c_track["title"]} - {c_track["track_artist"]} ({c_track["track_album"]})'

                expire_time = int(time.time())
                to_add = c_track['length']

                expire_time += to_add

                status_event = Event(
                    kind=30315,
                    content=status_content,
                    pub_key=user.public_key,
                    tags=[
                        ['d', 'music'],
                        ['expiration', str(expire_time)]
                    ]
                )

                print(status_event.content)

                try:
                    status_event.sign(user.private_key)
                    client.publish(status_event)
                except Exception as e:
                    print(e)

                last_title = c_track["title"]

        else:
            print(clementine.state)

        await asyncio.sleep(1)

    client.end()
    clementine.disconnect()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    try:
        asyncio.run(watch_tracks(get_config()))
    except ConfigError as ce:
        print(ce)



