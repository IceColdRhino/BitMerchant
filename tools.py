import json
import pandas as pd

# Library of useful tools used in multiple scripts

def df_filter(df,key,value):
    # Given a dataframe with a key name and value
    # Returns the subset of that dataframe where the key matches that value
    df = df[df[key]==value].reset_index(drop=True)
    return df

def json_load(table,region):
    # Loads a given json file as a pandas dataframe
    file_str = 'game_data/region-'+region+'/'+table+'.json'
    with open(file_str) as json_file:
        json_data = json.load(json_file)
    return pd.DataFrame(json_data)