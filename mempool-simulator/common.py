# common functions betweent he two simulations
import json 
import os.path

fee_ranges = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 17, 20, 25, 30, 40, 50, 60, 70, 80, 100, 120, 140, 170, 200, 250, 300, 400, 500, 600, 700, 800, 1000, 1200, 1400, 1700, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 10000]

PROBLEMATIC_INTERVALS = [[1516728783, 1516729440], [1515943500, 1515944160]] 

FIRST_BLOCK_HEIGHT_DURING_CONGESTION = 498084
FIRST_BLOCK_HEIGHT_NO_CONGESTION = 716644

MEMPOOL_DIR_DURING_CONGESTION = "../mempool-during-congestion"
MEMPOOL_DIR_NO_CONGESTION = "../mempool-no-congestion"

LMC_MAX_EDGES = 63251
LWMC_MAX_CAPACITY = 246436727385

NEO4J_MAX_CUT_EDGES_UNWEIGHTED = 62249
NEO4J_MAX_CUT_CAPACITY_WEIGHTED = 258711667453

LMC_RESULTS_K = { # maps k to LMC results (TODO: make this automatic)
  10: {
    "n_edges" : 15725,
    "capacity" : 827.08,
    "unit" : "BTC"
  },
  30: {
    "n_edges" : 26729,
    "capacity" : 1514.4,
    "unit" : "BTC"
  },
  100: {
    "n_edges" : 42062,
    "capacity" : 1931.48,
    "unit" : "BTC"
  },
  300: {
    "n_edges" : 52892,
    "capacity" : 1989.91,
    "unit" : "BTC"
  }
}

LWMC_RESULTS_K = { # maps k to LWMC results (TODO: make this automatic)
  10: {
    "n_edges" : 10911,
    "capacity" : 1199.89,
    "unit" : "BTC"
  },
  30: {
    "n_edges" : 20084,
    "capacity" : 1685.13,
    "unit" : "BTC"
  },
  100: {
    "n_edges" : 35447,
    "capacity" : 2107.7,
    "unit" : "BTC"
  },
  300: {
    "n_edges" : 44522,
    "capacity" : 2312.47,
    "unit" : "BTC"
  }
}

# We read the JSON file containing blocks data (height, number of transactions)

blocks_file = open("../blocks/blocks.json", mode = 'r')
blocks_data_content = blocks_file.read()
blocks_data = json.loads(blocks_data_content)

#FIRST_BLOCK_HEIGHT = FIRST_BLOCK_HEIGHT_DURING_CONGESTION
MEMPOOL_DIR = MEMPOOL_DIR_DURING_CONGESTION

def get_problematic_intervals():
  return PROBLEMATIC_INTERVALS

def get_blocks_data():
  return blocks_data

def get_first_block_height_during_congestion():
  return FIRST_BLOCK_HEIGHT_DURING_CONGESTION

def get_first_block_height_no_congestion():
  return FIRST_BLOCK_HEIGHT_NO_CONGESTION

def get_mempool_dir_during_congestion():
  return MEMPOOL_DIR_DURING_CONGESTION

def get_mempool_dir_no_congestion():
  return MEMPOOL_DIR_NO_CONGESTION

def get_lmc_max_edges():
  return LMC_MAX_EDGES

def get_lwmc_max_capacity():
  return LWMC_MAX_CAPACITY

def get_neo4j_max_edges_unweighted():
  return NEO4J_MAX_CUT_EDGES_UNWEIGHTED

def get_neo4j_max_capacity_weighted():
  return NEO4J_MAX_CUT_CAPACITY_WEIGHTED

def get_lmc_results():
  return LMC_RESULTS_K

def get_lwmc_results():
  return LWMC_RESULTS_K

def doPreprocessing(mempool_dir): # returns mempool data (preprocessed) 
  MEMPOOL_DIR = mempool_dir
  i = 1
  mempool_data_json_string = ''

  while os.path.exists(f"{MEMPOOL_DIR}/{i}_mempool"):
      mempool_data_file = open(f"{MEMPOOL_DIR}/{i}_mempool", mode = 'r')
      mempool_data_content = mempool_data_file.read()
      
      # We replace call() from file content (it is used for the website to load the JSONP)
      mempool_data_content = mempool_data_content[5 : len(mempool_data_content) - 2]
      
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

def get_median_index_fee(snapshot):

    tx_count_per_fee_level = snapshot[1]
    tx_count_per_fee_level = tx_count_per_fee_level[1:]
    total_tx_count = sum(tx_count_per_fee_level)

    # Computing the index of the median fee in `fee_ranges` (in the first snapshot of the simulation)

    acc = 0
    i = 0
    median_index = 0

    for c in tx_count_per_fee_level:
        acc = acc + c
        if acc >= total_tx_count / 2:
            # As soon as we detected that half of all the txs in the mempool have a lower fee 
            # than the current fee index (and half have an higher fee), than this is the median fee index
            median_index = i
            break
        else:
            i = i + 1  

    return median_index    
       
def get_average_index_fee(snapshot): 

    tx_count_per_fee_level = snapshot[1]
    tx_count_per_fee_level = tx_count_per_fee_level[1:]
    total_tx_count = sum(tx_count_per_fee_level)

    # Computing the index of the average fee in `fee_ranges` (in the first snapshot of the simulation)

    acc = 0
    i = 0

    while(i < len(tx_count_per_fee_level)):
        acc = acc + (fee_ranges[i] * tx_count_per_fee_level[i])
        i = i + 1

    avg_fee = acc / total_tx_count
    average_index = find_index_of_fee_in_ranges(avg_fee)

    return average_index  

def find_index_of_fee_in_ranges(fee):
    fee_index = 0
    i = 1

    while i < len(fee_ranges):
        if fee_ranges[i-1] <= fee and fee < fee_ranges[i]:
            fee_index = i-1
            return fee_index
        i = i + 1

    return len(fee_ranges) - 1 
