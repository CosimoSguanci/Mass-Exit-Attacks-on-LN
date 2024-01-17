import os
import base64
import codecs
import json
import requests
from hashlib import sha256
from secrets import token_hex
import shutil
import time
from subprocess import check_output, STDOUT
import subprocess
import shlex
import logging
import pexpect
from datetime import datetime

fee_ranges = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 17, 20, 25, 30, 40, 50, 60, 70, 80, 100, 120, 140, 170, 200,
              250, 300, 400, 500, 600, 700, 800, 1000, 1200, 1400, 1700, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 10000]

ENVIRONMENT = ''
def get_environment_home():
    return "/home/user"

ENVIRONMENT_HOME = get_environment_home()
LOGGER = None
CHANNEL_CAPACITY = 8390410
MAX_BLOCK_WEIGHT_FRACTION = 0.01 # percentage of the block weight used (e.g., if 0.25, the max block weight used in 25% of that in bitcoin)
K = 30  # Size of the adversarial coalition
N_ATTACKED_CHANNELS = int(26729*MAX_BLOCK_WEIGHT_FRACTION)  # Number of attacked channels
BITCOIN_CLI_PATH = f"{ENVIRONMENT_HOME}/Desktop/bitcoin-25.1/src"
FIRST_BLOCK_HEIGHT_DURING_CONGESTION = 498084
TO_SELF_DELAY = -1
FORCE_CLOSE_FEE_RATE = 0
CONFIRMED_FORCE_CLOSE = {}
FORCE_CLOSE_TXIDS = []
ACCUMULATED_TXS = 0
MINER_ADDRESS = ""
RESULTS_DIR = f"{ENVIRONMENT_HOME}/Desktop/results-zombie"
BITCOIN_DIR = f"{ENVIRONMENT_HOME}/.bitcoin/regtest"
VICTIM_PUBKEY = ""
ATTACKER_PUBKEY = ""
WATCHTOWER_PUBKEY = ""
ROOT_DIR = f"{ENVIRONMENT_HOME}/Desktop/mass-exit-network-sim"
DEV_DIR = f"{ENVIRONMENT_HOME}/Desktop/LN-analysis"
LN_EXE_DIR = f"{ENVIRONMENT_HOME}/Desktop/lnd-executables"
VICTIM_DIR = f"{ROOT_DIR}/.lnd-victim"
ATTACKER_DIR = f"{ROOT_DIR}/.lnd-attacker"
LND1_COMMAND = f"{LN_EXE_DIR}/lnd --lnddir={VICTIM_DIR} --accept-keysend"
LND2_COMMAND = f"{LN_EXE_DIR}/lnd --lnddir={ATTACKER_DIR} --accept-keysend"
LNCLI1_COMMAND = f"{LN_EXE_DIR}/lncli -n regtest --lnddir={VICTIM_DIR}"
LNCLI2_COMMAND = f"{LN_EXE_DIR}/lncli -n regtest --lnddir={ATTACKER_DIR} --rpcserver=localhost:11009"

LND_CONF_VICTIM = f"""
[Bitcoin]
bitcoin.active=1
bitcoin.regtest=1
bitcoin.node=bitcoind
bitcoin.defaultremotedelay={TO_SELF_DELAY}
[Bitcoind]
bitcoind.rpchost=127.0.0.1:8332
bitcoind.rpcuser=user
bitcoind.rpcpass=psw
bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333
[Application Options]
maxpendingchannels=1500
max-commit-fee-rate-anchors=1000
maxlogfiles=20
maxlogfilesize=200
"""

LND_CONF_ATTACKER = """
[Bitcoin]
bitcoin.active=1
bitcoin.regtest=1
bitcoin.node=bitcoind
[Application Options]
listen=0.0.0.0:9734
rpclisten=127.0.0.1:11009
restlisten=0.0.0.0:8180
maxlogfiles=20
maxlogfilesize=500
maxpendingchannels=1500
max-commit-fee-rate-anchors=1000
[Bitcoind]
bitcoind.rpchost=127.0.0.1:8332
bitcoind.rpcuser=user
bitcoind.rpcpass=psw
bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333
[sweeper]
sweeper.batchwindowduration=1s
"""

def setup_logs():
    global LOGGER
    if LOGGER is not None:
        LOGGER.handlers.clear()
    LOGGER = logging.getLogger(__name__)
    format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",datefmt="%H:%M:%S")
    LOGGER.setLevel(logging.DEBUG)
    logFile = logging.FileHandler(f"{DEV_DIR}/network-simulation/simulation-zombie.log")
    logFile.setLevel(logging.DEBUG)
    fileformat = format
    logFile.setFormatter(fileformat)
    LOGGER.addHandler(logFile)
    stream = logging.StreamHandler()
    streamformat = format
    stream.setFormatter(streamformat)
    LOGGER.addHandler(stream)

def clean_logs():
    if os.path.exists(f"{DEV_DIR}/network-simulation/simulation-zombie.log"):
        os.remove(f"{DEV_DIR}/network-simulation/simulation-zombie.log")

def clean_dirs():
    LOGGER.info("Cleaning directories...")

    shutil.rmtree(ROOT_DIR, ignore_errors=True)
    shutil.rmtree(BITCOIN_DIR, ignore_errors=True)

def setup_lnd_nodes():
    LOGGER.info("Creating directories...")

    os.makedirs(ROOT_DIR, exist_ok=True)
    os.makedirs(VICTIM_DIR, exist_ok=True)
    os.makedirs(ATTACKER_DIR, exist_ok=True)

    with open(f'{VICTIM_DIR}/lnd.conf', "w+") as lnd_conf:
        lnd_conf.write(LND_CONF_VICTIM)

    with open(f'{ATTACKER_DIR}/lnd.conf', "w+") as lnd_conf:
        lnd_conf.write(LND_CONF_ATTACKER)

def open_channels():

    LOGGER.info("Opening channels...")

    REST_HOST = 'localhost:8080'
    MACAROON_PATH = f'{VICTIM_DIR}/data/chain/bitcoin/regtest/admin.macaroon'
    TLS_PATH = f'{VICTIM_DIR}/tls.cert'
    url = f'https://{REST_HOST}/v1/channels'
    macaroon = codecs.encode(open(MACAROON_PATH, 'rb').read(), 'hex')
    headers = {'Grpc-Metadata-macaroon': macaroon}

    reqData = {
        'node_pubkey_string': ATTACKER_PUBKEY,
        'local_funding_amount': 0,
        'spend_unconfirmed': True
    }

    # We open all the channels
    for i in range(N_ATTACKED_CHANNELS):
        reqData["local_funding_amount"] = CHANNEL_CAPACITY
        r = requests.post(url, headers=headers,
                          data=json.dumps(reqData), verify=TLS_PATH)
        print(r.json())

        generate_blocks(1)
        time.sleep(1)
        LOGGER.info(f"Channel {i+1} created...")

    generate_blocks(2)
    LOGGER.info("Channels opened")
    time.sleep(5) 

def force_close_channels():
    LOGGER.info("Force-closing channels...")
    channels = list_channels()
    close_pending_list = []
    i = 0
    for chan in channels:
        funding_tx_id = chan["channel_point"][:chan["channel_point"].index(
            ":")]
        output_index = chan["channel_point"][chan["channel_point"].index(
            ":") + 1:]
        close_pending = force_close_channel(funding_tx_id, output_index)
        close_pending_list.append(close_pending)
        time.sleep(1)
        LOGGER.info(f"Force-closed channel {i+1}")
        i += 1
    LOGGER.info("All channels are being force-closed")
    return close_pending_list


def force_close_channel(funding_tx_id, output_index):
    REST_HOST = 'localhost:8080'
    MACAROON_PATH = f'{VICTIM_DIR}/data/chain/bitcoin/regtest/admin.macaroon'
    TLS_PATH = f'{VICTIM_DIR}/tls.cert'
    url = f'https://{REST_HOST}/v1/channels/{funding_tx_id}/{output_index}?force=true'
    macaroon = codecs.encode(open(MACAROON_PATH, 'rb').read(), 'hex')
    headers = {'Grpc-Metadata-macaroon': macaroon}
    r = requests.delete(url, headers=headers, stream=True, verify=TLS_PATH)
    for raw_response in r.iter_lines():
        json_response = json.loads(raw_response)
        print(json_response)
        return json_response["result"]["close_pending"]

def list_channels():
    REST_HOST = 'localhost:8080'
    MACAROON_PATH = f'{VICTIM_DIR}/data/chain/bitcoin/regtest/admin.macaroon'
    TLS_PATH = f'{VICTIM_DIR}/tls.cert'
    url = f'https://{REST_HOST}/v1/channels'
    macaroon = codecs.encode(open(MACAROON_PATH, 'rb').read(), 'hex')
    headers = {'Grpc-Metadata-macaroon': macaroon}
    r = requests.get(url, headers=headers, verify=TLS_PATH)
    r = r.json()
    channels = r["channels"]
    return channels

def compute_tx_fee_from_txid(txid):
    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getrawtransaction {txid} 1"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    return compute_tx_fee_from_raw_tx(output)

def compute_tx_fee_from_raw_tx(rawtx):
    rawtx_hex = rawtx["hex"]
    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli decoderawtransaction {rawtx_hex}"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    decodedrawtx = json.loads(output)
    vSize = decodedrawtx['vsize']
    output_value = 0
    for vout in decodedrawtx["vout"]:
        output_value += vout["value"]
    vin = decodedrawtx["vin"]
    input_value = 0
    for input in vin:
        if "coinbase" in input:
            break
        vout_index = input["vout"]
        vout_txid = input["txid"]
        command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getrawtransaction {vout_txid} 1"
        output = check_output(shlex.split(command), stderr=STDOUT).decode()
        rawtx = json.loads(output)
        rawtx_hex = rawtx["hex"]
        command = f"{BITCOIN_CLI_PATH}/bitcoin-cli decoderawtransaction {rawtx_hex}"
        output = check_output(shlex.split(command), stderr=STDOUT).decode()
        decodedrawtx = json.loads(output)
        for output in decodedrawtx["vout"]:
            if output["n"] == vout_index:
                input_value += output["value"]
                break
    fee_paid = (input_value - output_value) * pow(10, 8)
    fee_rate = fee_paid / vSize
    return fee_rate

def generate_blocks(n):
    LOGGER.info(f"Generating {n} new blocks...")
    r = subprocess.check_output(shlex.split(f"{BITCOIN_CLI_PATH}/bitcoin-cli -generate " + str(n)), stderr=STDOUT).decode()
    print(r)

def generate_initial_congestion():
    LOGGER.info("Generating initial congestion from mempool dataset...")
    mempool_data = doPreprocessing(f"{DEV_DIR}/mempool-during-congestion")
    force_close_fee_rate = find_index_of_fee_in_ranges(FORCE_CLOSE_FEE_RATE)
    # Array that contains, for each fee level in `fee_ranges`, the corresponding number of transactions currently in the mempool
    tx_count_per_fee_level = mempool_data[0][1].copy()
    for i in range(len(tx_count_per_fee_level)):
        LOGGER.info(
            f"Generating initial congestion for fee rate {str(fee_ranges[i])} sat/vByte")
        fee_rate = -1
        if i == len(fee_ranges) - 1:
            fee_rate = fee_ranges[i]+1
        else:
            fee_rate = (fee_ranges[i]+fee_ranges[i+1])/2
        if i == force_close_fee_rate:
            fee_rate = fee_ranges[i+1]-1
        fee_rate = str(fee_rate)
        r = subprocess.check_output(shlex.split(f"{BITCOIN_CLI_PATH}/bitcoin-cli -rpcclienttimeout=0 -named sendtoaddressmultiple address=\"2Mwu4nQiayYZ3ptuD6Pos1ES1E1vAJHbe2p\" amount=0.0001 n_txs={int(tx_count_per_fee_level[i] * MAX_BLOCK_WEIGHT_FRACTION)} fee_rate={fee_rate}"), stderr=STDOUT)
        print(r)
        LOGGER.info(
            f"Generated initial congestion for fee rate {str(fee_ranges[i])} sat/vByte")

    return mempool_data

def generate_initial_blocks(): 
    time.sleep(2)
    LOGGER.info("Creating bitcoin-core wallet")

    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli createwallet mywallet"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    print(output)

    LOGGER.info("Generating initial blocks...")

    n = 5000
    subprocess.Popen(f"{BITCOIN_CLI_PATH}/bitcoin-cli -rpcclienttimeout=0 -generate {n}",
                     stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
    
    blocks_generated = False
    while not blocks_generated:
        time.sleep(2)
        command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getblockchaininfo"
        output = check_output(shlex.split(command), stderr=STDOUT).decode()
        output = json.loads(output)
        if output["blocks"] == n:
            blocks_generated = True

    LOGGER.info(f"{n} initial blocks generated...")

# utility function to discard problematic intervals in the historical mempool dataset
def _isInProblematicInterval(timestamp):
    PROBLEMATIC_INTERVALS = [
        [1516728783, 1516729440], [1515943500, 1515944160]]

    for interval in PROBLEMATIC_INTERVALS:
        if timestamp >= interval[0] and timestamp < interval[1]:
            return True
    return False

def find_index_of_fee_in_ranges(fee):
    fee_index = 0
    i = 1

    while i < len(fee_ranges):
        if fee_ranges[i-1] <= fee and fee < fee_ranges[i]:
            fee_index = i-1
            return fee_index
        i = i + 1

    return len(fee_ranges) - 1

def get_local_tx_count_per_fee_level():
    local_tx_count_per_fee_level = []
    for _ in range(len(fee_ranges)):
        local_tx_count_per_fee_level.append(0)
    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getrawmempool true"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    mempool = list(output.items())
    mempool = [lambda_tx_mempool(tx) for tx in mempool]
    mempool.sort(reverse=True, key=get_key_sort_mempool)

    for tx in mempool:
        local_tx_count_per_fee_level[find_index_of_fee_in_ranges(
            tx[1]["fee_rate"])] += 1 

    return local_tx_count_per_fee_level

def check_end_condition():
    force_closed_channels = 0
    for force_close_txid in FORCE_CLOSE_TXIDS:
        if force_close_txid in CONFIRMED_FORCE_CLOSE:
            force_closed_channels += 1
            continue
        else:
            command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getrawtransaction {force_close_txid} 1"
            output = check_output(shlex.split(command), stderr=STDOUT).decode()
            output = json.loads(output)
            if "blockhash" in output:
                CONFIRMED_FORCE_CLOSE[force_close_txid] = True
                force_closed_channels += 1
    
    if force_closed_channels > 0:
        LOGGER.info(f"{force_closed_channels} force closed zombie channels")
    return force_closed_channels == N_ATTACKED_CHANNELS


def execute_simulation_using_mempool_dataset(mempool_data, blocks_data):
    current_block_number = 0
    last_total_tx_count = None
    last_tx_count_per_fee_level = None

    victim_sweeps = get_victim_pending_sweep_list()

    for sweep in victim_sweeps:
        if sweep["witness_type"] == 'COMMITMENT_ANCHOR':
            corresponding_force_close_txid = sweep["outpoint"][:sweep["outpoint"].index(
                ":")]        
            if not corresponding_force_close_txid in PENDING_SWEEPS_COMMITMENT_ANCHOR:
                PENDING_SWEEPS_COMMITMENT_ANCHOR[corresponding_force_close_txid] = sweep

    force_close_fee_index = find_index_of_fee_in_ranges(FORCE_CLOSE_FEE_RATE)

    LOGGER.info("Starting the main simulation using historical mempool and blocks data...")

    for snapshot in mempool_data:
        timestamp = snapshot[0]
        tx_count_per_fee_level = snapshot[1].copy()
        total_tx_count = sum(tx_count_per_fee_level)

        if last_total_tx_count is None and last_tx_count_per_fee_level is None:
            # First snapshot
            last_tx_count_per_fee_level = tx_count_per_fee_level.copy()
            last_total_tx_count = total_tx_count
            continue

        # "Problematic" intervals are intervals in which probably the node of the owner of the website that gives the dataset
        # went offline for sometime
        is_in_problematic_interval = _isInProblematicInterval(timestamp)

        txs_added = 0
        if total_tx_count < last_total_tx_count and not is_in_problematic_interval:
            # New Block, we must add transactions to the mempool to keep the congestion updated
            LOGGER.info(f"[timestamp={timestamp}] New block")
            LOGGER.info("Last tx count per fee level:")
            LOGGER.info(last_tx_count_per_fee_level)
            local_tx_count_per_fee_level = get_local_tx_count_per_fee_level()

            for i in range(len(last_tx_count_per_fee_level)):
                n = int(last_tx_count_per_fee_level[i] * MAX_BLOCK_WEIGHT_FRACTION) - local_tx_count_per_fee_level[i]
                if n > 0:
                    fee_rate = -1
                    if i == len(fee_ranges) - 1:
                        fee_rate = fee_ranges[i]+1
                    else:
                        fee_rate = (fee_ranges[i]+fee_ranges[i+1])/2     
                    if i == force_close_fee_index: 
                        fee_rate = fee_ranges[i]+1
                    fee_rate = str(fee_rate)    
                    r = subprocess.check_output(shlex.split(f"{BITCOIN_CLI_PATH}/bitcoin-cli -rpcclienttimeout=0 -named sendtoaddressmultiple address=\"2Mwu4nQiayYZ3ptuD6Pos1ES1E1vAJHbe2p\" amount=0.0001 n_txs={n} fee_rate={fee_rate}"), stderr=STDOUT)          
                    print(r)
                    LOGGER.info(f"{n} transactions added at fee index {i} to the mempool")
                    txs_added += n
            LOGGER.info(f"{txs_added} transactions added to the mempool")
            new_local_tx_count_per_fee_level = get_local_tx_count_per_fee_level()
            t = new_local_tx_count_per_fee_level.copy()
            LOGGER.info("Local tx count per fee level [AFTER ADDING TXS]:")
            for i in range(len(t)):
               t[i] = t[i] * 100
            LOGGER.info(t)
            LOGGER.info(f'Number of transactions in mempool before new block [HISTORICAL DATA]: {sum(last_tx_count_per_fee_level)}')
            LOGGER.info(f'Number of transactions in mempool before new block [LOCAL DATA, multiplied by 100]: {sum(t)}')
            blocksCount = get_new_blocks_count(snapshot, blocks_data, current_block_number, FIRST_BLOCK_HEIGHT_DURING_CONGESTION, last_total_tx_count)
            for i in range(blocksCount):
                output_newblock = generate_block_from_data(blocks_data, current_block_number, FIRST_BLOCK_HEIGHT_DURING_CONGESTION)
                if output_newblock is not None:
                    LOGGER.info(output_newblock)
                else:
                    LOGGER.warning("Not enough transactions in historical blocks to create a new block")
                current_block_number += 1
                LOGGER.info(f"Generated block {current_block_number} of simulation")

                if check_end_condition():
                    LOGGER.info(f"Simulation ended after {current_block_number} blocks")
                    return True
        last_total_tx_count = total_tx_count
        last_tx_count_per_fee_level = tx_count_per_fee_level.copy()

def get_victim_list_sweeps():
    command = f"{LNCLI1_COMMAND} wallet listsweeps"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    if "transaction_ids" in output["Sweeps"]["TransactionIds"]:
        return output["Sweeps"]["TransactionIds"]["transaction_ids"]
    else:
        return [] 

def get_victim_pending_channels():
    command = f"{LNCLI1_COMMAND} pendingchannels"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    return output["waiting_close_channels"]

def get_victim_pending_sweep_list():
    command = f"{LNCLI1_COMMAND} wallet pendingsweeps"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    return output["pending_sweeps"]

def lambda_tx_mempool(tx):
    txid = tx[0]
    txbody = tx[1]
    txbody["fee_rate"] = (txbody["fees"]["modified"] *
                          pow(10, 8)) / txbody["vsize"]
    return [txid, txbody]

def get_key_sort_mempool(tx):
    return tx[1]["fee_rate"]

def generate_block_from_data(blocks, blocksCounter, firstBlockHeightOfSimulation):
    global ACCUMULATED_TXS
    num_tx = int(blocks[(firstBlockHeightOfSimulation - blocks[0]["height"] +
                 blocksCounter)]["n_transactions"]*MAX_BLOCK_WEIGHT_FRACTION)
    ACCUMULATED_TXS = ACCUMULATED_TXS + ((blocks[(firstBlockHeightOfSimulation - blocks[0]["height"] +
                 blocksCounter)]["n_transactions"]*MAX_BLOCK_WEIGHT_FRACTION) - num_tx)
    LOGGER.info(f"We have {ACCUMULATED_TXS} accumulated transactions...")
    if ACCUMULATED_TXS > 1:
        num_tx += int(ACCUMULATED_TXS)
        ACCUMULATED_TXS = ACCUMULATED_TXS - int(ACCUMULATED_TXS)

    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getrawmempool true"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    mempool = list(output.items())
    mempool = [lambda_tx_mempool(tx) for tx in mempool]
    mempool.sort(reverse=True, key=get_key_sort_mempool)

    list_sweeps = get_victim_list_sweeps()
    
    while True:
        try:
            if num_tx == 0:
                return None

            txid_list = "'["

            block_tx_count = 0
            i = 0

            while block_tx_count < int(num_tx):
                next_txid = mempool[i][0]
                skip = False
                if next_txid in list_sweeps:
                    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getrawtransaction {next_txid} 1"
                    output = check_output(shlex.split(command), stderr=STDOUT).decode()
                    output = json.loads(output)

                    vin = output["vin"]

                    for txinput in vin:
                        if txinput["txid"] in PENDING_SWEEPS_COMMITMENT_ANCHOR and not txinput["txid"] in CONFIRMED_FORCE_CLOSE:
                            LOGGER.info(f"Skipping tx with txid={next_txid} to avoid bad-txns-inputs-missingorspent error")
                            skip = True
                            break
                if not skip:
                    txid_list += f"\"{mempool[i][0]}\","
                    block_tx_count += 1
                i += 1


            txid_list = txid_list[:-1]
            txid_list += "]'"

            command = f"{BITCOIN_CLI_PATH}/bitcoin-cli generateblock \"{MINER_ADDRESS}\" {txid_list}"
            output = check_output(shlex.split(command), stderr=STDOUT).decode()
            output = json.loads(output)
            print(output)
            LOGGER.info(f"Generated block containing {num_tx} transactions")
            return output
        except subprocess.CalledProcessError as e:
            if "bad-blk-length" in str(e.output):
                LOGGER.info("bad-blk-length error while generating a block, trying to decrease number of transactions")
                num_tx -= 1
                continue
            if "bad-blk-weight" in str(e.output):
                LOGGER.info("bad-blk-weight error while generating a block, trying to decrease number of transactions")
                num_tx -= 1
                continue
            else:
                raise Exception(str(e.output))

def b64_hex_transform(plain_str):
    a_string = bytes.fromhex(plain_str)
    return base64.b64encode(a_string).decode()


def b64_transform(plain_str):
    return base64.b64encode(plain_str.encode()).decode()


def get_blocks_data():
    blocks_file = open(f"{DEV_DIR}/blocks/blocks.json", mode='r')
    blocks_data_content = blocks_file.read()
    blocks_data = json.loads(blocks_data_content)
    return blocks_data


def doPreprocessing(mempool_dir):  

    MEMPOOL_DIR = mempool_dir
    i = 1
    mempool_data_json_string = ''

    while os.path.exists(f"{MEMPOOL_DIR}/{i}_mempool"):
        mempool_data_file = open(f"{MEMPOOL_DIR}/{i}_mempool", mode='r')
        mempool_data_content = mempool_data_file.read()

        # We replace call() from file content (it is used for the website to load the JSONP)
        mempool_data_content = mempool_data_content[5: len(
            mempool_data_content) - 2]

        # We remove the first and the last square brackets, then I will add them again at the end before parsing the JSON,
        # in order to obtain a single merged json of all the mempool data
        mempool_data_content = mempool_data_content[1:]
        mempool_data_content = mempool_data_content[:-1]

        mempool_data_content += ','

        mempool_data_json_string += mempool_data_content
        mempool_data_file.close()

        i += 1

    mempool_data_json_string = mempool_data_json_string[:-1]
    mempool_data_json_string = f"[{mempool_data_json_string}]"

    # Parsing JSON file

    mempool_data = json.loads(mempool_data_json_string)
    return mempool_data

def start_bitcoind():
    LOGGER.info("Starting bitcoind...")

    subprocess.Popen([f'{BITCOIN_CLI_PATH}/bitcoind', '-fallbackfee=0.0002', '-daemon'],
                     stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    

def do_initial_operations():
    global VICTIM_PUBKEY
    global ATTACKER_PUBKEY
    global MINER_ADDRESS

    LOGGER.info("Performing initial operations...")

    command = f"{LNCLI1_COMMAND} getinfo"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    VICTIM_PUBKEY = output["identity_pubkey"]

    command = f"{LNCLI2_COMMAND} getinfo"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    ATTACKER_PUBKEY = output["identity_pubkey"]

    command = f"{LNCLI2_COMMAND} connect {VICTIM_PUBKEY}@127.0.0.1:9735"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)

    command = f"{LNCLI1_COMMAND} newaddress np2wkh"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    victim_address = output["address"]

    command = f"{LNCLI2_COMMAND} newaddress np2wkh"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)
    attacker_address = output["address"]

    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli sendtoaddress {victim_address} 500"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()

    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli sendtoaddress {attacker_address} 500"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()

    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli -generate 1"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    output = json.loads(output)

    command = f"{BITCOIN_CLI_PATH}/bitcoin-cli getnewaddress"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    MINER_ADDRESS = output[:-1]

# We run the LND instances by means of systemctl: the services must be placed in ~/.config/systemd/user
def create_and_start_lnd_instances():
    LOGGER.info("Starting victim's LND")

    command = "systemctl --user enable --now lnd1.service"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    print(output)
    time.sleep(1)

    child = pexpect.spawn(f'{LNCLI1_COMMAND} create')
    time.sleep(1)
    child.sendline('password')
    child.sendline('password')
    child.sendline('n')
    child.sendline('\n')
    child.interact()

    LOGGER.info("Starting attacker's LND")
    
    command = "systemctl --user enable --now lnd2.service"
    output = check_output(shlex.split(command), stderr=STDOUT).decode()
    print(output)
    time.sleep(1)

    child = pexpect.spawn(f'{LNCLI2_COMMAND} create')
    time.sleep(1)
    child.sendline('password')
    child.sendline('password')
    child.sendline('n')
    child.sendline('\n')
    child.interact()
    time.sleep(5)
    LOGGER.info("LND instances LAUNCHED")

def clean_processes():
    LOGGER.info("Cleaning old processes (bitcoind/LND)...")

    try:
        command = f"{BITCOIN_CLI_PATH}/bitcoin-cli stop"
        check_output(shlex.split(command), stderr=STDOUT).decode()
    except:
        pass

    command = "systemctl --user disable --now lnd1.service"
    check_output(shlex.split(command), stderr=STDOUT).decode()

    command = "systemctl --user disable --now lnd2.service"
    check_output(shlex.split(command), stderr=STDOUT).decode()

# Returns the number of new block to be confirmed (could be 1 or 2, if blocks were mined very close)
def get_new_blocks_count(snapshot, blocks, next_block_counter, firstBlockHeightOfSimulation, last_total_tx_count):
    tx_count_per_fee_level = snapshot[1]
    total_tx_count = sum(tx_count_per_fee_level)
    num_tx_first_block = blocks[(firstBlockHeightOfSimulation - blocks[0]["height"] + next_block_counter)]["n_transactions"]
    tx_diff = last_total_tx_count - total_tx_count
    first_block_timestamp = blocks[(firstBlockHeightOfSimulation - blocks[0]["height"] + next_block_counter)]["timestamp"]
    first_block_height = blocks[(firstBlockHeightOfSimulation - blocks[0]["height"] + next_block_counter)]["height"]
    second_block_timestamp = blocks[(firstBlockHeightOfSimulation - blocks[0]["height"] + next_block_counter + 1)]["timestamp"]
    second_block_height = blocks[(firstBlockHeightOfSimulation - blocks[0]["height"] + next_block_counter + 1)]["height"]
    firstBlockTime = datetime.fromtimestamp(first_block_timestamp)
    secondBlockTime = datetime.fromtimestamp(second_block_timestamp)
    t_diff = (secondBlockTime - firstBlockTime).total_seconds()
    is_two_blocks = (tx_diff >= num_tx_first_block + 1000) and (t_diff < 60)
    if is_two_blocks:
        LOGGER.info(f"Detected 2 blocks, timestamp={first_block_timestamp}, blocks_height=[{first_block_height}, {second_block_height}]")
    else:
        LOGGER.info(f"Detected 1 block, timestamp={first_block_timestamp}, block_height={first_block_height}")

    return 1 if not is_two_blocks else 2

def init_lnd_conf_victim():
    global LND_CONF_VICTIM
    LND_CONF_VICTIM = f"""
    [Bitcoin]
    bitcoin.active=1
    bitcoin.regtest=1
    bitcoin.node=bitcoind
    bitcoin.defaultremotedelay={TO_SELF_DELAY}
    [Bitcoind]
    bitcoind.rpchost=127.0.0.1:8332
    bitcoind.rpcuser=user
    bitcoind.rpcpass=psw
    bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
    bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333
    [Application Options]
    maxpendingchannels=1500
    max-commit-fee-rate-anchors=1000
    """

def init_ln_commands():
    if os.path.exists(f"{LN_EXE_DIR}/lnd"):
        os.remove(f"{LN_EXE_DIR}/lnd")
    if os.path.exists(f"{LN_EXE_DIR}/lncli"):
        os.remove(f"{LN_EXE_DIR}/lncli")
    shutil.copyfile(f"{LN_EXE_DIR}/lnd-{str(FORCE_CLOSE_FEE_RATE)}-sat", f"{LN_EXE_DIR}/lnd")
    shutil.copyfile(f"{LN_EXE_DIR}/lncli-{str(FORCE_CLOSE_FEE_RATE)}-sat", f"{LN_EXE_DIR}/lncli")
    os.system(f"chmod +x {LN_EXE_DIR}/lnd")
    os.system(f"chmod +x {LN_EXE_DIR}/lncli")

def sim():
    clean_logs()
    setup_logs()
    LOGGER.info(f"STARTING SIMULATION WITH FORCE CLOSE TX FEE RATE = {FORCE_CLOSE_FEE_RATE}, TO_SELF_DELAY = {TO_SELF_DELAY}")
    clean_processes()
    clean_dirs()
    setup_lnd_nodes()
    start_bitcoind()
    generate_initial_blocks()
    create_and_start_lnd_instances()
    do_initial_operations()
    open_channels()
    generate_initial_congestion()
    force_close_channels()
    pending_close_channels = get_victim_pending_channels()
    for pending_close_channel in pending_close_channels:
        FORCE_CLOSE_TXIDS.append(pending_close_channel["closing_txid"])
    LOGGER.info(f"FORCE_CLOSE_TXIDS SIZE: {len(FORCE_CLOSE_TXIDS)}")
    mempool_data = doPreprocessing(f"{DEV_DIR}/mempool-during-congestion")
    blocks = get_blocks_data()
    ret_val = execute_simulation_using_mempool_dataset(mempool_data, blocks)
    if not ret_val:
        return False
    LOGGER.info("END of simulation")
    return True


def main():

    experiments = [
        {
            "fee_rate": 90,
            "to_self_delay": 1
        }
    ]

    global TO_SELF_DELAY
    global FORCE_CLOSE_FEE_RATE
    global CONFIRMED_FORCE_CLOSE
    global FORCE_CLOSE_TXIDS
    global ACCUMULATED_TXS
    global PENDING_SWEEPS_COMMITMENT_ANCHOR

    for experiment in experiments:
        FORCE_CLOSE_FEE_RATE = experiment["fee_rate"]
        TO_SELF_DELAY = experiment["to_self_delay"]
        CONFIRMED_FORCE_CLOSE = {}
        FORCE_CLOSE_TXIDS = []
        PENDING_SWEEPS_COMMITMENT_ANCHOR = {}
        ACCUMULATED_TXS = 0
        init_lnd_conf_victim()
        init_ln_commands()
        sim()
        res_dir = f"{RESULTS_DIR}/force_close_fee_rate_{FORCE_CLOSE_FEE_RATE}"
        os.makedirs(res_dir, exist_ok=True)
        shutil.copytree(ROOT_DIR, f"{res_dir}/mass-exit-network-sim")
        shutil.copyfile(f"{DEV_DIR}/network-simulation/simulation-zombie.log", f"{res_dir}/simulation-zombie.log")    

if __name__ == '__main__':
    main()