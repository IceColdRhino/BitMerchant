import configparser
import os
from pathlib import Path
import tools

def main(timestamp):
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    region = config['options']['region']
    
    claim_list = list(config['claim_reportlist'].values())
    
    claims = tools.json_load('claim_state',region)
    
    for claim_id in claim_list:
        claim_name = tools.df_filter(claims,'entity_id',int(claim_id)).iloc[0]['name']
        report_dir = Path('reports/report-'+str(timestamp)+'/'+claim_name)
        base_str = claim_name+' '+str(timestamp)
        
        os.remove(report_dir / (base_str+' Activity Comparison.json'))
        os.remove(report_dir / (base_str+' Merchant Opportunities.json'))
        os.remove(report_dir / (base_str+' Price Catalog.json'))