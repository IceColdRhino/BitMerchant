# This script grabs a set of queryable game tables and saves them as json files
# Scope is limited to a single game region at a time, that the player must be logged in at

import configparser
import json
import os
from pathlib import Path
import re
import requests
import urllib3.util
from websockets import Subprotocol
from websockets.exceptions import WebSocketException
from websockets.sync.client import connect

uri = '{scheme}://{host}/v1/database/{module}/{endpoint}'
proto = Subprotocol('v1.json.spacetimedb')

def dump_tables(host, module, queries, auth=None):
    save_data = {}
    new_queries = None
    if isinstance(queries, str):
        queries = [queries]
    try:
        with connect(
                uri.format(scheme='wss', host=host, module=module, endpoint='subscribe'),
                additional_headers={"Authorization": auth} if auth else {},
                subprotocols=[proto],
                max_size=None,
                max_queue=None
        ) as ws:
            ws.recv(timeout=None)
            sub = json.dumps(dict(Subscribe=dict(
                request_id=1,
                query_strings=[
                    f'SELECT * FROM {q};' if isinstance(q, str) else
                    f'SELECT * FROM {q[0]} WHERE {q[1]} = {q[2]};'
                    for q in queries
                ]
            )))
            ws.send(sub)
            for msg in ws:
                data = json.loads(msg)
                if 'InitialSubscription' in data:
                    initial = data['InitialSubscription']['database_update']['tables']
                    for table in initial:
                        name = table['table_name']
                        rows = table['updates'][0]['inserts']
                        save_data[name] = [json.loads(row) for row in rows]
                    break
                elif 'TransactionUpdate' in data and 'Failed' in data['TransactionUpdate']['status']:
                    failure = data['TransactionUpdate']['status']['Failed']
                    if bad_table := re.match(r'`(\w*)` is not a valid table', failure):
                        bad_table = bad_table.group(1)
                        print('Invalid table, skipping and retrying: ' + bad_table)
                        new_queries = [
                            q for q in queries
                            if (isinstance(q, str) and q != bad_table)
                               or (isinstance(q, tuple) and q[0] != bad_table)
                        ]
                    break
    except WebSocketException as ex:
        raise ex

    if new_queries:
        return dump_tables(host, module, new_queries, auth=auth)

    return save_data

def save_tables(data_dir, subdir, tables):
    root = data_dir / subdir
    root.mkdir(exist_ok=True)

    def _get_sort(x):
        # incredibly ugly but ok
        return x.get('id', x.get('item_id', x.get('building_id', x.get('name', x.get('cargo_id', x.get('type_id', -1))))))

    for name, data in tables.items():
        data = sorted(data, key=_get_sort)
        with open(root / (name + '.json'), 'w') as f:
            json.dump(data, fp=f, indent=2)

def grab(region,region_tables):
    ## Load configuration and set constants
    #config = configparser.ConfigParser()
    #config.read('config.ini')
    #region = config['options']['region']

    data_dir = Path('game_data')
    data_dir.mkdir(exist_ok=True)

    global_host = os.getenv('BITCRAFT_SPACETIME_HOST')
    if not global_host:
        raise ValueError('BITCRAFT_SPACETIME_HOST not set')
    auth = os.getenv('BITCRAFT_SPACETIME_AUTH') or None

    # Specify tables to query
    #region_tables = [
    #    'buy_order_state',
    #    'claim_state',
    #    'claim_local_state',
    #    'sell_order_state'
    #]

    region_data = dump_tables(global_host, 'bitcraft-'+region, region_tables, auth)
    save_tables(data_dir, 'region-'+region, region_data)
    print('Data Succesfully Saved')