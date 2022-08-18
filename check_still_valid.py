from algosdk.v2client.indexer import IndexerClient
from pprint import pprint
from time import sleep
from datetime import date


def load_csv(data_loaction) -> dict:
    res = {}
    with open(data_loaction, 'r') as file:
        for row in file:
            row = row.split(',')
            if len(row[0]) == 58: # Only grab rows that start with an address
                res[row[0]] = float(row[1]) # res = {address: amount, ...}
    
    return res

def get_account_info(indexer: IndexerClient, account) -> list:
    acc_info: dict = indexer.account_info(account)
    try:
        for localstate in acc_info['account']['apps-local-state']:
            if localstate['id'] == 751668529:
                for keyvalue in localstate['key-value']:
                    if keyvalue['key'] == 'U1RBS0U=':
                        return keyvalue['value']['uint'], acc_info
    except:
        print(f'nothing found for account {account}')
    return 0, acc_info

def main():
    indexer = IndexerClient(indexer_address='https://mainnet-idx.algonode.cloud', indexer_token='')
    accs = load_csv('ESB - fixed.csv')
    kicked_accs = []
    # for every account in ESB we check how much the blockchain tells us it's holding, by key 'U1RBS0U=' (stake) in app 751668529
    for acc, amount in accs.items():
        # This is just for my own personal housekeeping, so I don't need to check the tiny ones. ADAO team should tho.
        if amount > 50:
            res, acc_info = get_account_info(indexer, acc)
            res = res/(10**6)
            if res + 0.001 < amount: # This +.001 is not needed, but I am a nice dude (also to eliminate float rounding errors, but we save state so can check easily).
                kicked_accs.append([acc, res, amount, acc_info])

    with open(f'kicked-{date.today()}.csv', 'w') as file:
        file.write('Account;Current staked amount;ESB stake;indexer.account_info()\n')
        for line in kicked_accs:
            file.write(f'{line[0]};{line[1]};{line[2]};{line[3]}\n')



if __name__ == '__main__':
    main()