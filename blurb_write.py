import numpy as np
import pandas as pd
from pathlib import Path

def main(timestamp):
    claim_name = 'Albern'
    
    report_dir = Path('reports/report-'+str(timestamp)+'/'+claim_name)
    act_str = claim_name+' '+str(timestamp)+' Activity Comparison.json'
    trd_str = claim_name+' '+str(timestamp)+' Merchant Opportunities.json'
    
    activities = pd.read_json(report_dir / act_str)
    trades = pd.read_json(report_dir / trd_str)
    
    # Write the opening header
    full_str = '## Volkov Market Report\n'
    full_str += '## Generated <t:'
    full_str += str(timestamp)
    full_str += ':F>, <t:'
    full_str += str(timestamp)
    full_str += ':R>\n_ _\n'
    
    # Write details on randomly selected featured activity
    activities = activities[activities['profit']>=0].reset_index(drop=True)
    act_ind = np.random.randint(0,len(activities))
    act_feat = activities.iloc[act_ind]
    full_str += '### Featured '
    full_str += claim_name
    full_str += ' Activity\n'
    full_str += act_feat['name']
    full_str += '\n'
    
    # Write the ingredients
    full_str += 'Ingredient Cost: '
    full_str += format(int(np.ceil(act_feat['cost'])),',')
    full_str += ' Hex Coin(s)\n'
    for entry in act_feat['input_list']:
        full_str += '- '
        full_str += str(np.round(entry['quantity'],3))
        full_str += 'x '
        full_str += entry['name']
        full_str += ' ['
        full_str += entry['rarity']
        full_str += '] '
        full_str += format(entry['price'],',')
        full_str += ' Hex Coin(s) Each, '
        if 'Default' in entry['method']:
            full_str += 'No Competing Claim Buy Order\n'
        else:
            full_str += entry['method']
            full_str += '\n'
    
    # Write the outputs
    full_str += 'Expected Return: '
    full_str += format(np.round(act_feat['return'],2),',')
    full_str += ' Hex Coin(s)\n'
    for entry in act_feat['output_list']:
        full_str += '- '
        full_str += str(np.round(entry['quantity'],3))
        full_str += 'x '
        full_str += entry['name']
        full_str += ' ['
        full_str += entry['rarity']
        full_str += '] '
        full_str += format(entry['price'],',')
        full_str += ' Hex Coin(s) Each, '
        if 'Default' in entry['method']:
            full_str += 'No Competing Claim Sell Order\n'
        else:
            full_str += entry['method']
            full_str += '\n'
    
    # Write details on randomly selected featured trade
    full_str += '\n### Featured '
    full_str += claim_name
    full_str += ' Trade\n'
    
            
    trades = trades[trades['buy_strategy'].str.contains('Immediate')]
    trades = trades[trades['sell_strategy'].str.contains('Immediate')].reset_index(drop=True)
    
    if len(trades) == 0:
        full_str += 'Currently, there are no immediate-sale trade opportunities.'
    else:
        trd_ind = np.random.randint(0,len(trades))
        trd_feat = trades.iloc[trd_ind]
        full_str += trd_feat['item_name']
        full_str += ' ['
        full_str += trd_feat['item_rarity']
        full_str += ']\n- Buy for '
        full_str += format(trd_feat['buy_price'],',')
        full_str += ' Hex Coin(s) in '
        full_str += trd_feat['origin_claim']
        full_str += '\n- Sell for '
        full_str += format(trd_feat['sell_price'],',')
        full_str += ' Hex Coin(s) in '
        full_str += trd_feat['destination_claim']
        full_str += '\n- ~ '
        full_str += format(trd_feat['distance'],',')
        full_str += ' Hex Tiles Apart\n- '
        full_str += str(int(trd_feat['stack_size']))
        full_str += ' to a stack'
    
    with open('reports/report-'+str(timestamp)+'/report_blurb.txt', "w") as f:
      f.write(full_str)