import configparser
import numpy as np
import pandas as pd
from pathlib import Path
import tools

def find_extrema(df,entry):
    # Find extrema of a market order at a specific item entry
    price_list = list(tools.df_filter(df,'item_id',entry['id'])['price_threshold'])

    if price_list == []:
        return (np.nan,np.nan)
    else:
        return (min(price_list),max(price_list))

def main(timestamp):
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    region = config['options']['region']
    claim_list = list(config['claim_reportlist'].values())
    
    for claim_id in claim_list:
        # It's a touch wasteful to reload all the tables,
        # and repeat all the formatting that's not claim-dependant
        # But the nested lists/dicts within the DataFrame has weird results
        # And doesn't play nice with inbuilt copying methods
        # So rebuilding them from scratch is just easier
        
        # Load Relevant Tables
        buy_orders = tools.json_load('buy_order_state',region)
        cargos = tools.json_load('cargo_desc',region)
        claims = tools.json_load('claim_state',region)
        items = tools.json_load('item_desc',region)
        item_lists = tools.json_load('item_list_desc',region)
        sell_orders = tools.json_load('sell_order_state',region)
        
        claim_name = tools.df_filter(claims,'entity_id',int(claim_id)).iloc[0]['name']
        
        # Filter the item and cargo dataframes only for relevant info, and then join them
        df_keep = ['id','name','volume','tier','tag','rarity','item_list_id']
        cargos['item_list_id'] = 0
        cargos = cargos[df_keep];           items = items[df_keep]
        cargos.insert(1,'type','Cargo');    items.insert(1,'type','Item')
        items = pd.concat([items,cargos]).reset_index(drop=True)
        # Combine type column into id column
        items['id'] = items['id'].astype(str)
        items['id'] = items['type']+'_'+items['id']
        items = items.drop(columns=['type'])
        
        # Replace type integers with strings on the id
        buy_orders['item_type'] = buy_orders['item_type'].astype(str)
        sell_orders['item_type'] = sell_orders['item_type'].astype(str)
        buy_orders.loc[buy_orders['item_type']=='0','item_type']='Item'
        buy_orders.loc[buy_orders['item_type']=='1','item_type']='Cargo'
        sell_orders.loc[sell_orders['item_type']=='0','item_type']='Item'
        sell_orders.loc[sell_orders['item_type']=='1','item_type']='Cargo'
        buy_orders['item_id'] = buy_orders['item_type']+'_'+buy_orders['item_id'].astype(str)
        sell_orders['item_id'] = sell_orders['item_type']+'_'+sell_orders['item_id'].astype(str)
        
        # Replace rarity structures with strings
        rarity_list = ['Default','Common','Uncommon','Rare',
                       'Epic','Legendary','Mythic']
        for i in range(0,len(items)):
            rarity_index = items.iloc[i]['rarity'][0]
            items.at[i,'rarity'] = rarity_list[rarity_index]
        
        # Filter for market orders within the given claim
        claim_buys = tools.df_filter(buy_orders,'claim_entity_id',int(claim_id))
        claim_sells = tools.df_filter(sell_orders,'claim_entity_id',int(claim_id))
        
        # Determine basic item values from market
        for i in range(0,len(items)):
            entry = items.iloc[i]
        
            # Immediately exit the loop in the case of item lists
            if entry['item_list_id'] != 0:
                continue
        
            # Find market buy/sell windows
            region_buy_item = find_extrema(buy_orders,entry)[1]
            region_sell_item = find_extrema(sell_orders,entry)[0]
            claim_buy_item = find_extrema(claim_buys,entry)[1]
            claim_sell_item = find_extrema(claim_sells,entry)[0]
        
            items.at[i,'max_claim_buy'] = claim_buy_item
            items.at[i,'max_region_buy'] = region_buy_item
            items.at[i,'min_region_sell'] = region_sell_item
            items.at[i,'min_claim_sell'] = claim_sell_item
        
            # Determine the input price, in order of priority
            if claim_buy_item is not np.nan:
                input_price = claim_buy_item+1
                input_method = 'Overbid Highest Claim Buy Order'
            else:
                input_price = 1
                input_method = 'Default to 1'
        
            # Determine the output price, in order of priority
            if claim_sell_item is not np.nan:
                output_price = claim_sell_item-1
                output_method = 'Undercut Lowest Claim Sell Order'
            elif claim_buy_item is not np.nan:
                output_price = claim_buy_item
                output_method = 'Match Highest Claim Buy Order'
            else:
                output_price = 1
                output_method = 'Default to 1'
        
        
            # Record results
            items.at[i,'input_price'] = input_price
            items.at[i,'output_price'] = output_price
            items.at[i,'input_notes'] = [{
                'id':entry['id'],
                'name':entry['name'],
                'rarity':entry['rarity'],
                'quantity':1,
                'price':input_price,
                'method':input_method
            }]
            items.at[i,'output_notes'] = [{
                'id':entry['id'],
                'name':entry['name'],
                'rarity':entry['rarity'],
                'quantity':1,
                'price':output_price,
                'method':output_method
            }]
        
        # TODO: Add claim supply purchases
        # TODO: Add NPC trade good sales
        
        # Grab a list of item lists that are in the dataframe
        drop_lists = items['item_list_id'].unique()
        drop_lists = [x for x in drop_lists if x != 0]
        
        # Iterate across the list, striking completed items from the list, and
        # sending uncompletable items to the back of the list.
        # This should catch any nested lists the devs sneak in at a future date
        # (except for any self-referencing lists)
        while len(drop_lists) > 0:
            list_id = drop_lists[0]
            
            list_indices = items.index[items['item_list_id']==list_id].tolist()
            
            list_entry = item_lists[item_lists['id']==list_id].iloc[0]
            
            possibilities = list_entry['possibilities']
            new_list = []
            prob_sum = 0
            for possibility in possibilities:
                poss_prob = possibility[0]
                prob_sum += poss_prob
                item_stack_list = possibility[1]
                
                for item_stack in item_stack_list:
                    # Match id to "items" dataframe format
                    if item_stack[2][0] == 0:
                        item_stack[0] = 'Item_'+str(item_stack[0])
                    elif item_stack[2][0] == 1:
                        item_stack[0] = 'Cargo_'+str(item_stack[0])
                    
                    # Note the quantity of the list
                    quantity = item_stack[1]
                    
                    # Grab the relevant output notes
                    note_list = items[items['id']==item_stack[0]]['output_notes'].to_list()[0]
                    if note_list is np.nan:
                        # If an item is encountered which doesn't have a note list
                        print(item_stack[0])
                        # TODO: Actually handle this case
                        ...
                    for note in note_list:
                        new_note = note.copy()
                        new_note['quantity'] = new_note['quantity']*quantity*poss_prob
                        new_list.append(new_note)
            
            # Collapse duplicate note entries into each other
            temp_df = pd.DataFrame(new_list)
            temp_df = temp_df.groupby(['id','name','rarity','price','method'],as_index=False).sum()
            temp_df['quantity'] = temp_df['quantity']/prob_sum
            temp_df.insert(4, 'quantity', temp_df.pop('quantity'))
            new_list = temp_df.to_dict('records')
            
            # Record Output
            for list_index in list_indices:
                items.at[list_index,'output_notes'] = new_list
                items.at[list_index,'output_price'] = sum(x['quantity']*x['price'] for x in new_list)
            
            # Strike the id entry from the list
            del drop_lists[0]
        
        # Save the generated catalog
        report_dir = Path('reports/report-'+str(timestamp)+'/'+claim_name)
        report_dir.mkdir(exist_ok=True,parents=True)
        file_str = claim_name+' '+str(timestamp)+' Price Catalog'
        
        items = items.sort_values('name',ascending=True).reset_index(drop=True)
        items = items.round(2)
        items.to_csv(report_dir / (file_str+'.csv'),index=False)
        items.to_json(report_dir / (file_str+'.json'),orient='records')
        print('Compiled '+claim_name+' Price Catalog')