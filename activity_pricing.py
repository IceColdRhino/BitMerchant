import configparser
import numpy as np
import pandas as pd
from pathlib import Path
import tools

def input_stack_notes(input_stacks,catalog):
    # Given a list of output stacks and a catalog,
    # returns the compiled notes from the given items
    input_list = []
    
    for input_stack in input_stacks:
        if input_stack[2][0] == 0:
            input_stack[0] = 'Item_'+str(input_stack[0])
        elif input_stack[2][0] == 1:
            input_stack[0] = 'Cargo_'+str(input_stack[0])
            
        if len(input_stack) == 4:
            # Give a "100% consumption chance" to item conversion stacks
            input_stack.append(1)
        quantity = input_stack[1]
        consumption = input_stack[4]
        
        selection = tools.df_filter(catalog,'id',input_stack[0])
        
        input_notes = selection.at[0,'input_notes']

        if input_notes is not None:
            for note in input_notes:
                temp_note = note.copy()
                temp_note['quantity'] = float(quantity*consumption*temp_note['quantity'])
                input_list.append(temp_note)
    return input_list

def output_stack_notes(output_stacks,catalog):
    # Given a list of output stacks and a catalog,
    # returns the compiled notes from the given items
    output_list = []
    for output_stack in output_stacks:
        if output_stack[2][0] == 0:
            output_stack[0] = 'Item_'+str(output_stack[0])
        elif output_stack[2][0] == 1:
            output_stack[0] = 'Cargo_'+str(output_stack[0])
            
        quantity = output_stack[1]
        
        selection = tools.df_filter(catalog,'id',output_stack[0])
    
        output_notes = selection.at[0,'output_notes']
        
        if output_notes is not None:
            for note in output_notes:
                temp_note = note.copy()
                temp_note['quantity'] = quantity*temp_note['quantity']
                output_list.append(temp_note)
    
    return output_list

def main(timestamp):
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    region = config['options']['region']
    
    skill_list = [
        'None','Any','Forestry','Carpentry','Masonry','Mining','Smithing',
        'Scholar','Leatherworking','Hunting','Tailoring','Farming','Fishing',
        'Cooking','Foraging','Construction','Exploration','Taming','Slayer',
        'Trading','LoreKeeper','Sailing']
    
    claim_list = list(config['claim_reportlist'].values())
    
    
    for claim_id in claim_list:
        # Loading and reformatting EVERYTHING is a little wastefule
        # But dicts and dataframes and lists have some strong-reference stuff
        # and iterables aren't really meant to go INSIDE dataframes...
        # So, this is just easier
        
        # Load relevant tables
        cargos = tools.json_load('cargo_desc',region)
        claims = tools.json_load('claim_state',region)
        converts = tools.json_load('item_conversion_recipe_desc',region)
        crafts = tools.json_load('crafting_recipe_desc',region)
        enemies = tools.json_load('enemy_desc',region)
        extracts = tools.json_load('extraction_recipe_desc',region)
        items = tools.json_load('item_desc',region)
        resources = tools.json_load('resource_desc',region)
        
        # Items and cargos are only here for name lookup
        # We can be messy and join them together
        items['id'] = 'Item_'+items['id'].astype(str)
        cargos['id'] = 'Cargo_'+cargos['id'].astype(str)
        items = pd.concat([items, cargos])
        
        claim_name = tools.df_filter(claims,'entity_id',int(claim_id)).iloc[0]['name']
        report_dir = Path('reports/report-'+str(timestamp)+'/'+claim_name)
        catalog_str = claim_name+' '+str(timestamp)+' Price Catalog.json'
        
        catalog = pd.read_json(report_dir / catalog_str)
        
        
        # Filter the craft and extraction dataframes only for relevant info,
        # and then join them
        df_keep = ['id','name','base_time','base_stamina','effort','cost','return',
                   'profit','hex_per_second','hex_per_stam','hex_per_effort']
        max_l = -1
        
        
        # Initializing some (no, not all) new columns
        crafts.at[0,'input_list'] = ['initialize']
        crafts.at[0,'output_list'] = ['placeholder']
        crafts['id'] = 'Craft_'+crafts['id'].astype(str)
        crafts['base_time'] = crafts['time_requirement']*crafts['actions_required']
        crafts['base_stamina'] = crafts['stamina_requirement']*crafts['actions_required']
        crafts['effort'] = crafts['actions_required']
        for i in range(0,len(crafts)):    
            level_list = crafts.at[i,'level_requirements']
            for l in range(0,len(level_list)):
                if l > max_l:
                    max_l = l
                crafts.at[i,'skill_req_'+str(l)] = skill_list[level_list[l][0]]
                crafts.at[i,'lvl_req_'+str(l)] = level_list[l][1]
                
            input_list = input_stack_notes(crafts.at[i,'consumed_item_stacks'],catalog)
            output_list = output_stack_notes(crafts.at[i,'crafted_item_stacks'],catalog)
            if '{0}' in crafts.at[i,'name']:
                try:
                    name_0 = tools.df_filter(
                        items,'id',crafts.at[i,'crafted_item_stacks'][0][0]
                        ).at[0,'name']
                except:
                    name_0 = '{0}'
                crafts.at[i,'name'] = crafts.at[i,'name'].replace('{0}',name_0)
            if '{1}' in crafts.at[i,'name']:
                try:
                    name_1 = tools.df_filter(
                        items,'id',crafts.at[i,'consumed_item_stacks'][0][0]
                        ).at[0,'name']
                except:
                    name_1 = '{1}'
                crafts.at[i,'name'] = crafts.at[i,'name'].replace('{1}',name_1)
            crafts.at[i,'input_list'] = input_list
            crafts.at[i,'output_list'] = output_list
            crafts.at[i,'cost'] = sum(x['quantity']*x['price'] for x in input_list)
            crafts.at[i,'return'] = sum(x['quantity']*x['price'] for x in output_list)
        print('     Analyzed '+claim_name+' Crafting Activities')
        
        
        
        # Trim out extractions that reference cargos instead of resources
        extracts = extracts[extracts['resource_id']!=0].reset_index(drop=True)
        extracts['id'] = 'Extract_'+extracts['id'].astype(str)
        extracts.at[0,'input_list'] = ['initialize']
        extracts.at[0,'output_list'] = ['placeholder']
        for i in range(0,len(extracts)):
            resource = tools.df_filter(resources,'id',extracts.iloc[i]['resource_id']).iloc[0]
            extracts.at[i,'name'] = extracts.at[i,'verb_phrase']+' '+resource['name']
            extracts.at[i,'base_time'] = extracts.at[i,'time_requirement']*resource['max_health']
            extracts.at[i,'base_stamina'] = extracts.at[i,'stamina_requirement']*resource['max_health']
            extracts.at[i,'effort'] = resource['max_health']
            
            level_list = extracts.at[i,'level_requirements']
            for l in range(0,len(level_list)):
                if l > max_l:
                    max_l = l
                extracts.at[i,'skill_req_'+str(l)] = skill_list[level_list[l][0]]
                extracts.at[i,'lvl_req_'+str(l)] = level_list[l][1]
            
            prob_outputs = extracts.at[i,'extracted_item_stacks']
            output_stacks = []
            for entry in prob_outputs:
                entry[0][1][1] = entry[0][1][1]*entry[1]
                output_stacks.append(entry[0][1])
            input_list = input_stack_notes(extracts.at[i,'consumed_item_stacks'],catalog)
            output_list = output_stack_notes(output_stacks,catalog)
            for entry in input_list:
                entry['quantity'] = entry['quantity']*resource['max_health']/10
            for entry in output_list:
                entry['quantity'] = entry['quantity']*resource['max_health']
            extracts.at[i,'input_list'] = input_list
            extracts.at[i,'output_list'] = output_list
            extracts.at[i,'cost'] = sum(x['quantity']*x['price'] for x in input_list)
            extracts.at[i,'return'] = sum(x['quantity']*x['price'] for x in output_list)
        print('     Analyzed '+claim_name+' Gathering Activities')
        
        enemies['id'] = 'Kill_'+enemies['enemy_type'].astype(str)
        enemies['base_time'] = np.nan
        enemies['base_stamina'] = np.nan
        enemies['cost'] = 0
        enemies['effort'] = enemies['max_health']
        enemies['skill_req_0'] = 'Hunting'
        enemies.at[0,'input_list'] = ['initialize']
        enemies.at[0,'output_list'] = ['placeholder']
        for i in range(0,len(enemies)):
            if enemies.at[i,'huntable']:
                enemies.at[i,'name'] = 'Hunt '+enemies.at[i,'name']
            else:
                enemies.at[i,'name'] = 'Slay '+enemies.at[i,'name']
                
            if enemies.at[i,'tier'] > 2:
                # This is a proxy for tool requirement
                # i.e., a T5 animal can be killed with a T4 tool
                # which requires lvl 30 to equip
                enemies.at[i,'lvl_req_0'] = (enemies.at[i,'tier']-1)*10
            else:
                enemies.at[i,'lvl_req_0'] = 1
                
            prob_outputs = enemies.at[i,'extracted_item_stacks']
            output_stacks = []
            for entry in prob_outputs:
                entry[0][1][1] = entry[0][1][1]*entry[1]
                output_stacks.append(entry[0][1])
            output_list = output_stack_notes(output_stacks,catalog)
            enemies.at[i,'input_list'] = []
            enemies.at[i,'output_list'] = output_list
            enemies.at[i,'return'] = sum(x['quantity']*x['price'] for x in output_list)
        print('     Analyzed '+claim_name+' Hunting Activities')
        
        # Trim out conversion of type "Resolve" that self-reference
        converts = converts[converts['name'].str.contains('Resolve')==False].reset_index(drop=True)
        converts['id'] = 'Convert_'+converts['id'].astype(str)
        converts['base_time'] = converts['time_cost']
        converts['base_stamina'] = converts['stamina_cost']
        converts['effort'] = 1
        # Theoretically, conversions can have tool/tier requirements
        # However, they're currently all set to 0
        converts['skill_req_0'] = 'Any'
        converts['lvl_req_0'] = 1
        for i in range(0,len(converts)):
            input_list = input_stack_notes(converts.at[i,'input_items'],catalog)
            output_list = output_stack_notes([list(converts.iloc[i]['output_item'][1].values())],catalog)
            converts.at[i,'input_list'] = input_list
            converts.at[i,'output_list'] = output_list
            converts.at[i,'cost'] = sum(x['quantity']*x['price'] for x in input_list)
            converts.at[i,'return'] = sum(x['quantity']*x['price'] for x in output_list)
        print('     Analyzed '+claim_name+' Unpacking Activities')
        
        
        for l in range(0,max_l+1):
            df_keep += ['skill_req_'+str(l),'lvl_req_'+str(l)]
        df_keep += ['input_list','output_list']
        
        
        activities = pd.concat([
            crafts,
            extracts,
            enemies,
            converts
            ]).reset_index(drop=True)
        
        activities['profit'] = activities['return'] - activities['cost']
        activities['hex_per_second'] = activities['profit']/activities['base_time']
        activities['hex_per_stam'] = activities['profit']/activities['base_stamina']
        activities['hex_per_effort'] = activities['profit']/activities['effort']
        
        activities = activities[df_keep]
        
        # Save the generated comparison
        file_str = claim_name+' '+str(timestamp)+' Activity Comparison'
        activities = activities.sort_values('hex_per_effort',ascending=False).reset_index(drop=True)
        activities = activities.round(4)
        activities.to_csv(report_dir / (file_str+'.csv'),index=False)
        activities.to_json(report_dir / (file_str+'.json'),orient='records')
        print('Compiled '+claim_name+' Activity Comparison')