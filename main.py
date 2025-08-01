import activity_pricing
import blurb_write
import cleanup
import configparser
import data_grabber
import datetime
import item_valuer
import trade_searcher

def main():
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')

    region = config['options']['region']

    snapshot = datetime.datetime.now(datetime.UTC)
    timestamp = int(snapshot.timestamp())

    if config['options']['update_desc_tables'] == 'True':
        region_tables = [
                'cargo_desc',
                'crafting_recipe_desc',
                'enemy_desc',
                'extraction_recipe_desc',
                'item_conversion_recipe_desc',
                'item_desc',
                'item_list_desc',
                'resource_desc'
            ]
        print('Updating desc tables.')
        data_grabber.grab(region,region_tables)
        print('Updated desc tables, per config settings. Exiting script.')
        quit()
    else:
        region_tables = [
                'buy_order_state',
                'claim_local_state',
                'claim_state',
                'sell_order_state'
            ]
        print('Grabbing snapshot of state tables.')
        data_grabber.grab(region,region_tables)
        print('Updated state tables. Proceeding with report analysis.')

    item_valuer.main(timestamp)
    activity_pricing.main(timestamp)
    trade_searcher.main(timestamp)
    blurb_write.main(timestamp)
    #cleanup.main(timestamp)

    print('Report Completed')

if __name__ == '__main__':
    main()