from algosdk.v2client.indexer import IndexerClient
from time import sleep
from collections import defaultdict

indexer_client = IndexerClient(indexer_address='https://mainnet-idx.algonode.cloud', indexer_token='')

START_BLOCK = 21791634
END_BLOCK = indexer_client.health().get('round')
def load_csv(data_loaction) -> dict:
    res = {}
    with open(data_loaction, 'r') as file:
        for row in file:
            row = row.split(',')
            if len(row[0]) == 58: # Only grab rows that start with an address
                res[row[0]] = float(row[1]) # res = {address: amount, ...}
    
    return res

def populated_kicked():
    kicked_accs_accs = []
    try:
        with open('kickedv2.csv', 'r') as file:
            for row in file:
                row = row.split(';')
                if len(row) == 5 and len(row[0]) == 58: # Only grab rows that contain an address
                    kicked_accs_accs.append(row[0])
    except:
        return []
    return kicked_accs_accs

def get_account_txs(indexer: IndexerClient, account) -> list:
    cr = indexer.search_transactions_by_address(address=account, limit=1000000, min_round=START_BLOCK, max_round=END_BLOCK)
    res = cr['transactions']
    while 'next-token' in cr:
        sleep(0.02)
        cr = indexer.search_transactions_by_address(address=account, limit=1000000, min_round=START_BLOCK, max_round=END_BLOCK, next_page=cr['next-token'])
        if cr['transactions']:
            res.append(cr['transactions'])
    return res

def main():
    """Run this file with the current ESB-data in a csv namned 'ESB - fixed.csv'. This generates a new file 'kicked.csv' with all the accounts
    to be kicked from the ESB program. If ran consequtive times new accounts will be added to 'kicked.csv', with no duplicates."""
    
    accs = load_csv('ESB - fixed.csv')
    bad_accounts = {}
    kicked_accs = populated_kicked()
    for acc, amount in accs.items():
        if acc in kicked_accs:
            continue
        txs = get_account_txs(indexer_client, acc)
        if acc == "P2SN4WNOJ3BDEXKFSENICQAKCLVKXWEZLKSUSAMTQM4ETPQG7UTVA6PLIE":
            print(txs)
            input("asdf")
        for tx in txs:
            ap = "application-transaction"
            dt = "local-state-delta"
            if dt in tx and ap in tx and tx[ap]['application-id'] == 751668529:
                for lvar in tx[dt][0]['delta']:
                    if lvar.get('key') == "U1RBS0U=":
                        c_stake = lvar['value']['uint']/(10**6)
                        if c_stake+0.001 < amount:
                            if acc not in bad_accounts:
                                info = {'ESB_stake': amount, 'low': c_stake, 'dropped_round': tx["confirmed-round"], 'tx_id': tx['id']}
                                bad_accounts[acc] = info
    
    print(f'Found {len(bad_accounts)} new bad accounts.')

    try:
        with open(f'kickedv2.csv', 'x') as file:
            file.write("Account;ESB stake;Too low stake;Round;Transaction ID\n")
            for acc, info in bad_accounts.items():
                file.write(f'{acc};{info["ESB_stake"]};{info["low"]};{info["dropped_round"]};{info["tx_id"]}\n')
    except:
        with open(f'kickedv2.csv', 'a') as file:
            for acc, info in bad_accounts.items():
                file.write(f'{acc};{info["ESB_stake"]};{info["low"]};{info["dropped_round"]};{info["tx_id"]}\n')

if __name__ == '__main__':
    main()