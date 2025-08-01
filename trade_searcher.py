import configparser
import numpy as np
import pandas as pd
from pathlib import Path
import tools

# Ignore errors I know for a fact will occur, and I don't care about
np.seterr(divide='ignore', invalid='ignore')

def write_trade(start,end,strats,item_id,dist):
    claim_name_0 = start[0]
    claim_name_1 = end[0]
    catalog_0 = start[1]
    catalog_1 = end[1]
    buy_strategies = strats[0]
    sell_strategies = strats[1]
    
    item_0 = tools.df_filter(catalog_0,'id',item_id).iloc[0]
    item_1 = tools.df_filter(catalog_1,'id',item_id).iloc[0]
    sub_dict = []
    
    stack_size = 0
    if 'Item' in item_id:
        stack_size = np.round(6000/item_0['volume'])
    elif 'Cargo' in item_id:
        stack_size = np.round(60000/item_0['volume'])
        
    for buy_strat in buy_strategies:
        if 'Overbid' in buy_strat:
            buy = item_0['max_claim_buy']+1
        elif 'Match' in buy_strat:
            buy = item_0['min_claim_sell']
        
        for sell_strat in sell_strategies:
            if 'Undercut' in sell_strat:
                sell = item_1['min_claim_sell']-1
            elif 'Match' in sell_strat:
                sell = item_1['max_claim_buy']
    
            sub_dict.append(
                {'origin_claim':claim_name_0,
                 'destination_claim':claim_name_1,
                 'distance':dist,
                 'item_id':item_id,
                 'item_name':item_0['name'],
                 'item_tag':item_0['tag'],
                 'item_tier':item_0['tier'],
                 'item_rarity':item_0['rarity'],
                 'buy_price':buy,
                 'buy_strategy':buy_strat,
                 'sell_price':sell,
                 'sell_strategy':sell_strat,
                 'profit':sell-buy,
                 'profit_factor':(sell-buy)/buy,
                 'item_volume':item_0['volume'],
                 'stack_size':stack_size,
                 'stack_profit_per_tile':((sell-buy)*stack_size)/dist
                 }
                )
    return sub_dict
            
def main(timestamp):
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')

    region = config['options']['region']

    # Load relevant tables
    claims = tools.json_load('claim_state',region)
    claim_locals = tools.json_load('claim_local_state',region)


    claim_list = list(config['claim_reportlist'].values())

    buy_strategies = [
        'Delayed - Overbid Highest Buy Order',
        'Immediate - Match Lowest Sell Order'
        ]
    sell_strategies = [
        'Delayed - Undercut Lowest Sell Order',
        'Immediate - Match Highest Buy Order'
        ]

    for claim_id_0 in claim_list:
        main_dict = []

        claim_0 = tools.df_filter(claim_locals,'entity_id',int(claim_id_0)).iloc[0]
        x0 = claim_0['location'][1]['x']
        z0 = claim_0['location'][1]['z']
        
        claim_name_0 = tools.df_filter(claims,'entity_id',int(claim_id_0)).iloc[0]['name']
        report_dir_0 = Path('reports/report-'+str(timestamp)+'/'+claim_name_0)
        catalog_str_0 = claim_name_0+' '+str(timestamp)+' Price Catalog.json'
        catalog_0 = pd.read_json(report_dir_0 / catalog_str_0)
        
        item_list = list(catalog_0['id'].unique())
        
        for claim_id_1 in claim_list:
            claim_1 = tools.df_filter(claim_locals,'entity_id',int(claim_id_1)).iloc[0]
            x1 = claim_1['location'][1]['x']
            z1 = claim_1['location'][1]['z']
            
            dist = int(np.round(np.sqrt(((x0-x1)**2) + ((z0-z1)**2))/3))
            
            claim_name_1 = tools.df_filter(claims,'entity_id',int(claim_id_1)).iloc[0]['name']
            report_dir_1 = Path('reports/report-'+str(timestamp)+'/'+claim_name_1)
            catalog_str_1 = claim_name_1+' '+str(timestamp)+' Price Catalog.json'
            catalog_1 = pd.read_json(report_dir_1 / catalog_str_1)
            
            start = [claim_name_0,catalog_0]
            end = [claim_name_1,catalog_1]
            strats = [buy_strategies,sell_strategies]
            
            for item_id in item_list:
                main_dict += write_trade(start,end,strats,item_id,dist)
                main_dict += write_trade(end,start,strats,item_id,dist)
            
            print('     Analyzed trades between '+claim_name_0+' and '+claim_name_1)
            
        trades = pd.DataFrame(main_dict)
        trades = trades[trades['profit']>=0]
        trades = trades.sort_values('profit',ascending=False).reset_index(drop=True)
        trades = trades.round(2)
        
        file_str = claim_name_0+' '+str(timestamp)+' Merchant Opportunities'
        trades.to_csv(report_dir_0 / (file_str+'.csv'),index=False)
        trades.to_json(report_dir_0 / (file_str+'.json'),orient='records')
        print('Compiled '+claim_name_0+' Merchant Opportunities')