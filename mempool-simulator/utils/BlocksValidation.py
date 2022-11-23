from datetime import datetime
import json
import os

PROBLEMATIC_INTERVALS = [[1516728783, 1516729440], [1515943500, 1515944160]] 
N = 8000 

def doPreprocessing(mempool_dir): 
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

def isInProblematicInterval(timestamp):
  for interval in PROBLEMATIC_INTERVALS:
    if timestamp >= interval[0] and timestamp < interval[1]:
      return True
  return False

def run(mempool_data, firstBlockHeightOfSimulation):
  f = open('blocks/blocks.json') 
  blocks_array = json.load(f)
  f.close()
  first_height_in_file = blocks_array[0]["height"]
  lastTotalTxCount = -1
  lastTxCountPerFeeLevel = None
  blocksCounter = 0
  firstBlockDone = False
  okBlocks = 0
  average_n_transactions = 0
  for snapshot in mempool_data:
      timestamp = snapshot[0]
      tx_count_per_fee_level = snapshot[1] # Array that contains, for each fee level in `fee_ranges`, the corresponding number of transactions currently in the mempool
      total_tx_count = sum(tx_count_per_fee_level)

      if lastTotalTxCount == -1 and lastTxCountPerFeeLevel is None:
          # First snapshot
          lastTotalTxCount = total_tx_count
          lastTxCountPerFeeLevel = tx_count_per_fee_level
      else:
          is_in_problematic_interval = isInProblematicInterval(timestamp)
          if not is_in_problematic_interval and total_tx_count < lastTotalTxCount:
              # New Block(s) detected
              if firstBlockDone:
                  blocksCounter += 1
              else:
                  firstBlockDone = True 

              num_tx_next_block = blocks_array[(firstBlockHeightOfSimulation - first_height_in_file + blocksCounter)]["n_transactions"]
              average_n_transactions += num_tx_next_block
              tx_diff = lastTotalTxCount - total_tx_count
              first_block_timestamp = blocks_array[(firstBlockHeightOfSimulation - first_height_in_file + blocksCounter)]["timestamp"]
              second_block_timestamp = blocks_array[(firstBlockHeightOfSimulation - first_height_in_file + blocksCounter) + 1]["timestamp"]
              firstBlockTime = datetime.fromtimestamp(first_block_timestamp)
              secondBlockTime = datetime.fromtimestamp(second_block_timestamp)
              t_diff = (secondBlockTime - firstBlockTime).total_seconds()
              is_two_blocks = (tx_diff >= num_tx_next_block + 1000) and (t_diff < 60)
              
              if is_two_blocks:
                blocksCounter += 1
                average_n_transactions += blocks_array[(firstBlockHeightOfSimulation - first_height_in_file + blocksCounter)]["n_transactions"]
                print(f"two blocks: {datetime.fromtimestamp(timestamp)}, {firstBlockHeightOfSimulation + blocksCounter - 1}, {firstBlockHeightOfSimulation + blocksCounter}")


              if blocksCounter >= N:
                break

          lastTotalTxCount = total_tx_count
          lastTxCountPerFeeLevel = tx_count_per_fee_level 

  #print(f"{100*(okBlocks/blocksCounter)}% of ok blocks")
  print(f"on avg {average_n_transactions/blocksCounter} txs per block")


mempool_data_during_congestion = doPreprocessing('mempool-during-congestion')
run(mempool_data_during_congestion, 498084)

  
  