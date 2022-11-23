from simulation.Simulation import Simulation
from datetime import datetime

class ComplexModeSimulation(Simulation):

  def __init__(self, mempoolData, blocksData, isDynamic, useHistoricalBlocksData, firstBlockHeightOfSimulation, problematicIntervals, step, beta):
    super().__init__(mempoolData, blocksData, isDynamic, useHistoricalBlocksData, firstBlockHeightOfSimulation, problematicIntervals, step, beta)
    self._userTxsPerFeeLevel = [ [] for _ in range(len(self._getAllFeeRanges())) ]
    self._txToBeAdded = [0] * len(self._getAllFeeRanges())
    self._currentMempoolIndex = 0
    self._confirmedTxCount = 0
    self._firstBlockDone = False

  def getTxWithSameFee(self, feeIndex):
    return self._lastTxCountPerFeeLevel[feeIndex] + self._txToBeAdded[feeIndex] 
  
  def getAverageFee(self, txsWithNumGreaterThanOne): # txsWithNumGreaterThanOne: transactions with tx.num > 1, temporary solution
    tx_count_per_fee_level = self._getFullTxCountPerFeeLevel(txsWithNumGreaterThanOne)
    total_tx_count = sum(tx_count_per_fee_level)
    acc = 0
    i = 0
    while i < len(tx_count_per_fee_level):
      acc = acc + (self._getAllFeeRanges()[i] * tx_count_per_fee_level[i])
      i = i + 1
    avg_fee = acc / total_tx_count
    average_index = self._findIndexOfFeeInRanges(avg_fee)
    return average_index, avg_fee
  
  def _getFullTxCountPerFeeLevel(self, txsWithNumGreaterThanOne):
    full_tx_count_per_fee_level = [0] * len(self._getAllFeeRanges())

    for i in range(len(self._getAllFeeRanges())):
      full_tx_count_per_fee_level[i] += txsWithNumGreaterThanOne[i] + self._lastTxCountPerFeeLevel[i] + self._txToBeAdded[i]
      if len(self._userTxsPerFeeLevel[i]) > 0:
        full_tx_count_per_fee_level[i] += (len(self._userTxsPerFeeLevel[i]) )
    return full_tx_count_per_fee_level

  def _findTxsToBeAdded(self, starting_fee_index, amount):
    index = starting_fee_index
    while amount > 0 and index >= 0:
      if(self._lastTxCountPerFeeLevel[index] >= amount):
        self._txToBeAdded[index] += amount
        amount = 0
      else:
        self._txToBeAdded[index] += self._lastTxCountPerFeeLevel[index]
        amount -= self._lastTxCountPerFeeLevel[index]
      index -= 1   

  def _decreaseTxWithSameFee(self, fee_index, amount):
    tmp = self._txToBeAdded[fee_index]
    self._txToBeAdded[fee_index] = max(self._txToBeAdded[fee_index] - amount, 0)
    self._lastTxCountPerFeeLevel[fee_index] -= (amount - (tmp - self._txToBeAdded[fee_index]))
    for tx in list(filter(lambda tx: tx is not None, self._userTxsPerFeeLevel[fee_index])):
      tx.txWithSameFee = max(tx.txWithSameFee - amount, 0)   

  def allUserTxsConfirmed(self):
    for txs in self._userTxsPerFeeLevel:
      if len(txs) > 0: return False    
    return True    
  
  def getConfirmedTxCount(self):
    return self._confirmedTxCount
  
  def getFirstSnapshot(self):
    if self._mempoolData is not None and len(self._mempoolData) > 0:
      return self._mempoolData[0]
    return None
      
  def submitTransaction(self, tx): # A new transaction is submitted to the mempool
    self._userTxsPerFeeLevel[tx.feeIndex].append(tx) 
  
  def hasSnapshots(self):
    return self._currentMempoolIndex < len(self._mempoolData)

  def _processBlock(self, tx_count_per_fee_level, num_tx_in_block):
    # As said before, user txs actually "replace" standard txs that would have been removed from the mempool
    # without user txs, therefore they should be re-added and considered for future blocks [FUTURE WORK].
        
    # We find the higher fee in user transactions
    highest_user_fee_index = 0
    i = len(self._getAllFeeRanges()) - 1
    while i >= 0:
      if len(self._userTxsPerFeeLevel[i]) > 0:
        highest_user_fee_index = i
        break
      i -= 1

    index = len(self._lastTxCountPerFeeLevel) - 1      
    confirmed_txs = 0
    # Now we confirm transactions that have a higher fee wrt our users' txs
    while index > highest_user_fee_index and confirmed_txs < num_tx_in_block:
      space_in_block = num_tx_in_block - confirmed_txs
      n_txs = self._lastTxCountPerFeeLevel[index] + self._txToBeAdded[index] 
      if n_txs <= space_in_block:
        self._lastTxCountPerFeeLevel[index] -= (n_txs - self._txToBeAdded[index])
        self._txToBeAdded[index] = 0
        confirmed_txs += n_txs
      else:
        tmp = self._txToBeAdded[index]
        self._txToBeAdded[index] = max(self._txToBeAdded[index] - space_in_block, 0)
        self._lastTxCountPerFeeLevel[index] -= (n_txs - (tmp - self._txToBeAdded[index]))
        confirmed_txs = num_tx_in_block
      index -= 1

    tx_to_be_confirmed = num_tx_in_block - confirmed_txs
    
    # As said before, user txs actually "replace" standard txs that would have been removed from the mempool
    # without user txs, therefore they must be re-added and considered for future blocks.
    amount_tx_to_be_added = 0
    starting_index_tx_to_be_added = 0

    if tx_to_be_confirmed > 0:
      # There is "space" for more transactions in the block
      fee_index = highest_user_fee_index
      
      while fee_index >= 0 and tx_to_be_confirmed > 0:     
        user_txs = self._userTxsPerFeeLevel[fee_index]
        
        if len(user_txs) > 0: # If there are user txs in this fee level
          tx_index = 0

          while tx_index < len(user_txs) and tx_to_be_confirmed > 0:
            tx = self._userTxsPerFeeLevel[fee_index][tx_index]
            
            # The "position" of txs in the mempool is modified
            if tx.txWithSameFee >= tx_to_be_confirmed:
              self._decreaseTxWithSameFee(fee_index, tx_to_be_confirmed)
              tx_to_be_confirmed = 0
              break # no more txs to confirm
            else:
              if tx.txWithSameFee > 0:
                tx_to_be_confirmed -= tx.txWithSameFee
                self._decreaseTxWithSameFee(fee_index, tx.txWithSameFee)
            
            if tx.num > 1:
              tmp = tx.num
              tx.num = max(tmp - tx_to_be_confirmed, 0)
              num_confirmed_txs = tmp - tx.num
              tx_to_be_confirmed -= num_confirmed_txs
              self._confirmedTxCount += num_confirmed_txs
              amount_tx_to_be_added += num_confirmed_txs
              starting_index_tx_to_be_added = tx.feeIndex
              
              if tx.num == 0:
                tx.confirmed = True
                tx.confirmedBlockNumber = self._blocksCounter
                # We put None placeholder values in the `ln_txs_per_fee_level` array to remove confirmed user txs after
                # all the txs that are included in the block are computed
                self._userTxsPerFeeLevel[fee_index][tx_index] = None
            else:
              tx.num -= 1
              tx_to_be_confirmed -= 1                        
              self._confirmedTxCount += 1
              tx.confirmed = True
              tx.confirmedBlockNumber = self._blocksCounter
              self._userTxsPerFeeLevel[tx.feeIndex][tx_index] = None
              amount_tx_to_be_added += 1
              starting_index_tx_to_be_added = tx.feeIndex
            
            tx_index += 1

        else:
          tmp = tx_to_be_confirmed
          tx_to_be_confirmed = max(tx_to_be_confirmed - self._txToBeAdded[fee_index], 0)
          self._txToBeAdded[fee_index] = max(self._txToBeAdded[fee_index] - (tmp - tx_to_be_confirmed), 0)
          tx_to_be_confirmed = max(tx_to_be_confirmed - self._lastTxCountPerFeeLevel[fee_index], 0)
        
        fee_index -= 1
      
      for i in range(len(self._userTxsPerFeeLevel)):
        self._userTxsPerFeeLevel[i] = list(filter(lambda tx: tx is not None, self._userTxsPerFeeLevel[i]))
    
    # If there are some `tx_to_be_added` to add, they are added to the corresponding fee_level in the array
    self._findTxsToBeAdded(starting_index_tx_to_be_added, amount_tx_to_be_added)
    
    # TODO: remove self._dynamic
    dynamicFeeIncrease = self._dynamic and self._blocksCounter % self._step == 0
    if dynamicFeeIncrease:
      tx_to_be_added_dynamically = []  

      for fee_index in range(len(self._userTxsPerFeeLevel)):
          for tx_index in range(len(self._userTxsPerFeeLevel[fee_index])):
              tx = self._userTxsPerFeeLevel[fee_index][tx_index]
              if tx.confirmed or not tx.dynamic: 
                  continue
              new_fee = tx.currentFee * self._beta
              tx.currentFee = new_fee
              new_fee_index = self._findIndexOfFeeInRanges(new_fee)

              if new_fee_index != tx.feeIndex:
                  tx.feeIndex = new_fee_index
                  tx.txWithSameFee = tx_count_per_fee_level[new_fee_index] + self._txToBeAdded[new_fee_index] 
                  self._userTxsPerFeeLevel[fee_index][tx_index] = None
                  tx_to_be_added_dynamically.append(tx)

      for i in range(len(self._userTxsPerFeeLevel)):
          self._userTxsPerFeeLevel[i] = list(filter(lambda tx: tx is not None, self._userTxsPerFeeLevel[i]))

      for tx in tx_to_be_added_dynamically:
        self._userTxsPerFeeLevel[tx.feeIndex].append(tx)

  # Returns the number of new block to be confirmed (could be 1 or 2, if blocks were mined very close)
  def getNewBlocksCount(self, nextBlockCounter):
    snapshot = self._mempoolData[self._currentMempoolIndex]
    tx_count_per_fee_level = snapshot[1]
    total_tx_count = sum(tx_count_per_fee_level)

    num_tx_first_block = self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + nextBlockCounter)]["n_transactions"]
    tx_diff = self._lastTotalTxCount - total_tx_count
    first_block_timestamp = self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + nextBlockCounter)]["timestamp"]
    second_block_timestamp = self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + nextBlockCounter) + 1]["timestamp"]
    firstBlockTime = datetime.fromtimestamp(first_block_timestamp)
    secondBlockTime = datetime.fromtimestamp(second_block_timestamp)
    t_diff = (secondBlockTime - firstBlockTime).total_seconds()
    is_two_blocks = (tx_diff >= num_tx_first_block + 1000) and (t_diff < 60) #(tx_diff > num_tx_first_block) and (t_diff < 60)
    
    return 1 if not is_two_blocks else 2

  def run(self, updateSnapshot=True):
    snapshot = self._mempoolData[self._currentMempoolIndex]

    timestamp = snapshot[0]
    tx_count_per_fee_level = snapshot[1].copy()
    total_tx_count = sum(tx_count_per_fee_level)

    if self._lastTotalTxCount is None and self._lastTxCountPerFeeLevel is None:
      # First snapshot
      self._lastTxCountPerFeeLevel = tx_count_per_fee_level.copy()
      self._lastTotalTxCount = total_tx_count
      return

    # "Problematic" intervals are intervals in which probably the node of the owner of the website that gives the dataset
    # went offline for sometime
    is_in_problematic_interval = self._isInProblematicInterval(timestamp)

    if total_tx_count < self._lastTotalTxCount and not is_in_problematic_interval:
      # New Block
      if self._firstBlockDone:
        self._blocksCounter += 1
      else:
        self._firstBlockDone = True 

      #print(f"[INFO] New Block (#{self._firstBlockHeightOfSimulation + self._blocksCounter}) detected")

      # On new block, we compute the number of transactions with a fee that is higher than user' txs
      # If this number is higher than the number of transactions in the block, no user txs are confirmed in this block.
      # Otherwise, some user txs could be included in the block, and we must check their current "position" in the mempool
      # at their fee level, i.e. how many txs there are in the same fee level that were submitted before them.
      
      num_tx_in_block = self._getTransactionsInNextBlock()#self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + self._blocksCounter)]["n_transactions"]
      self._processBlock(tx_count_per_fee_level, num_tx_in_block)

    if(updateSnapshot):
      self._lastTotalTxCount = total_tx_count
      self._lastTxCountPerFeeLevel = tx_count_per_fee_level.copy()
      self._currentMempoolIndex += 1