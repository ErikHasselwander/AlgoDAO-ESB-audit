from algosdk.v2client.indexer import IndexerClient
from pprint import pprint
from time import sleep

END_BLOCK = 21791634 # This is the block where the snapshot was taken
IDO_END_BLOCK = 21200000
START_BLOCK = 21165000  # This is before the IDO started, anything before this will not matter, since
                        # only IDO+DEX tokens should count to the ESB boost. 

STAKING_ADDRESS = 'EMEABVXQCF77HVWVJSFZQJGICHF2SKH7C4OINFS6ZGASIAHLVJFLTDBSTA'
IDO_SC_ADDRESS = 'NLPXUT2TLSVU7BPVZ23E3DST4X4TBG2MGKCMSWBYSFNU46KW7WDNWXRT7A'
ADAO_IDO_BOOST_VC_ADDRESSES = ['D7H2TD2JSTBQS4WFD4G5I3252AVYUJCTFB4AYKVCH7PQDDE326DBQ2WEJE', 'LVHM6KACKVJOZGNYTYMJARYGTWB4YEW7KVRFV5ZDAMMVGJB7VOC3OWGX2Q']
POOL_ADDRESSES = [
    'ZPXL7VYKHZI3KHFXLMT7EU74YM63VZO4A4AJYW2VPW57WJ6R5SJCG7JWE4', 
    '43W64CNOAH75N7QV3OOPYEOKB6KZFMI3RT2MVPFF7VXHMEL4S6TJ52DFSU', 
    'YV27USZVL6OQBY5P66KCZINCNPNGRK2Q5DSRJEIUHGJCLWLJQS3TEW4UGM', 
    'GC2SPP3KEBTO7ASPHUVMHPG2ABNK44MVZDSJUT34LDG7CJZMWITDJ3N7XA', 
    'C3IXXPDUOD7ODPSCECES4NE6FGDZ3XPWH6EAJ2BDSY3J2AEDNMTIOIVXWA', 
    '3HWQYPAHRVOSZAZWWMXEDYRTLIEENOH7GUMQUCUFR5WO7OEVGBLGO2MIVQ'
    ] # This data is available at https://free-api.vestige.fi/asset/692085161/pools?include_all=true

def load_csv(data_loaction) -> dict:
    res = {}
    with open(data_loaction, 'r') as file:
        for row in file:
            row = row.split(',')
            if len(row[0]) == 58: # Only grab rows that start with an address
                res[row[0]] = float(row[1]) # res = {address: amount, ...}
    
    return res

def get_transactions(indexer: IndexerClient, account, asset_id) -> list:
    cr = indexer.search_transactions_by_address(address=account, limit=10000, min_round=START_BLOCK, max_round=END_BLOCK, asset_id=asset_id)
    res = cr['transactions']
    while 'next-token' in cr:
        sleep(0.02)
        cr = indexer.search_transactions_by_address(address=account, limit=10000, min_round=START_BLOCK, max_round=END_BLOCK, asset_id=asset_id, next_page=cr['next-token'])
        if cr['transactions']:
            res.append(cr['transactions'])
    return res

def main():
    indexer = IndexerClient(indexer_address='https://mainnet-idx.algonode.cloud', indexer_token='')

    # We load all accounts into a dictionary
    accounts = load_csv('ESB - Wallet List - staking_info_before_block_21791634_provided_2022_07_11_19_24_45.csv')
    # For each account we load all the txs between the start and the end blocks. 
    count = 0
    for account in accounts:
        result = {
        'account': account,
        'illegal_adao_from_creator_wallet': {'sum': 0, 'txs': []}, # should at most be 1666,666666 (excluding NFTs, which we check manually).
        'adao_from_nft': 0,
        'adao_from_unknown': {'sum': 0, 'txs': []}, # Any adao from unknown wallets will be checked manually, to ensure its not a VC sending it around
        'usdc_into_ido': 0, # This is to track how much ADAO you are allowed to get from the creator.
        'adao_from_ido': 0,
        'adao_from_dex': 0, # Can be whatever
        'sum': 0,
        'on-sheet': accounts[account]
        }
        adao_txs = get_transactions(indexer, account, 692085161)
        usdc_txs = get_transactions(indexer, account, 31566704)

        for tx in adao_txs:
            if (tx['tx-type'] == 'axfer' and 
                tx['asset-transfer-transaction']['receiver'] == account and
                tx['asset-transfer-transaction']['amount'] > 0):
                if tx['sender'] in ADAO_IDO_BOOST_VC_ADDRESSES:
                    a = tx['asset-transfer-transaction']['amount']
                    if a == 555000000 or a == 1110000000 or a == 1666666667:
                        result['adao_from_nft'] += tx['asset-transfer-transaction']['amount']
                    else:
                        result['illegal_adao_from_creator_wallet']['sum'] += tx['asset-transfer-transaction']['amount']
                        result['illegal_adao_from_creator_wallet']['txs'].append(tx['id'])
                        result['sum'] -= tx['asset-transfer-transaction']['amount']
                elif tx['sender'] in POOL_ADDRESSES:
                    result['adao_from_dex'] += tx['asset-transfer-transaction']['amount']
                elif tx['sender'] == IDO_SC_ADDRESS:
                    result['adao_from_ido'] += tx['asset-transfer-transaction']['amount']
                else:
                    result['adao_from_unknown']['sum'] += tx['asset-transfer-transaction']['amount']
                    result['adao_from_unknown']['txs'].append(tx['id'])
                    result['sum'] -= tx['asset-transfer-transaction']['amount']

            if (tx['tx-type'] == 'appl' and 
                'inner-txns' in tx):
                for itx in tx['inner-txns']:
                    if (itx['tx-type'] == 'axfer' and 
                    itx['asset-transfer-transaction']['receiver'] == account and
                    itx['asset-transfer-transaction']['amount'] > 0):
                        if itx['sender'] in ADAO_IDO_BOOST_VC_ADDRESSES:
                            result['illegal_adao_from_creator_wallet']['sum'] += itx['asset-transfer-transaction']['amount']
                            result['illegal_adao_from_creator_wallet']['txs'].append(tx['id'])
                            result['sum'] -= itx['asset-transfer-transaction']['amount']
                        elif itx['sender'] in POOL_ADDRESSES:
                            result['adao_from_dex'] += itx['asset-transfer-transaction']['amount']
                        elif itx['sender'] == IDO_SC_ADDRESS:
                            result['adao_from_ido'] += itx['asset-transfer-transaction']['amount']
                        elif itx['sender'] == STAKING_ADDRESS:
                            pass
                        else:
                            result['adao_from_unknown']['sum'] += itx['asset-transfer-transaction']['amount']
                            result['adao_from_unknown']['txs'].append(tx['id'])
                            result['sum'] -= itx['asset-transfer-transaction']['amount']


        for tx in usdc_txs:
            if (tx['tx-type'] == 'axfer' and 
                tx['asset-transfer-transaction']['receiver'] == IDO_SC_ADDRESS):
                result['usdc_into_ido'] += tx['asset-transfer-transaction']['amount']
                result['sum'] -= tx['asset-transfer-transaction']['amount']/0.75 - tx['asset-transfer-transaction']['amount']/0.60
                result['adao_from_ido'] -= tx['asset-transfer-transaction']['amount']/0.75 - tx['asset-transfer-transaction']['amount']/0.60
                result['illegal_adao_from_creator_wallet']['sum'] += tx['asset-transfer-transaction']['amount']/0.75 - tx['asset-transfer-transaction']['amount']/0.60

        result['illegal_adao_from_creator_wallet']['sum'] = round(result['illegal_adao_from_creator_wallet']['sum']/10**6, 6)
        result['adao_from_unknown']['sum'] = round(result['adao_from_unknown']['sum']/10**6, 6)
        result['adao_from_ido'] = round(result['adao_from_ido']/10**6, 6)
        result['adao_from_dex'] = round(result['adao_from_dex']/10**6, 6)
        result['sum'] = round(result['sum']/10**6, 6)
        result['usdc_into_ido'] = round(result['usdc_into_ido']/10**6, 6)
        
        accounts[account] = result
        count += 1
        print(f'{round(100*count/(len(accounts)))}% of accounts have been proccessed')


    with open('result.csv', 'w') as file:
        file.write('Address;Conclusion;USDC in IDO;ADAO from IDO;ADAO from DEX;ADAO from NFT;Illegal ADAO from creators;Txns from creators;ADAO from unknown sources;Txns from unknown sources\n')
        for account in accounts:
            data = accounts[account]
            if data['sum'] < -100: # just some margin in case of rounding errors
                text = f"{account};{data['sum']};{data['usdc_into_ido']};{data['adao_from_ido']};{data['adao_from_dex']};{data['adao_from_nft']};{data['illegal_adao_from_creator_wallet']['sum']};{data['illegal_adao_from_creator_wallet']['txs']};{data['adao_from_unknown']['sum']};{data['adao_from_unknown']['txs']}\n" # {data['usdc_into_ido']}
                file.write(text)








if __name__ == '__main__':
    main()
