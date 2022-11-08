from simulation.Simulation import Simulation

fee_ranges =  [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 17, 20, 25, 30, 40, 50, 60, 70, 80, 100, 120, 140, 170, 200, 250, 300, 400, 500, 600, 700, 800, 1000, 1200, 1400, 1700, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 10000]

class ComplexModeSimulation(Simulation):

  def __init__(self, mempoolData, blocksData, isDynamic, firstBlockHeightOfSimulation, problematicIntervals, step, beta):
    super().__init__(mempoolData, blocksData, isDynamic, firstBlockHeightOfSimulation, problematicIntervals, step, beta)
    self._userTxsPerFeeLevel = [ [] for _ in range(len(fee_ranges)) ]
    self._txToBeAdded = [0] * len(fee_ranges)
    self._currentMempoolIndex = 0
    self._confirmedTxCount = 0
    self._noneTxsPerFeeLevel = []

  def getTxWithSameFee(self, feeIndex):
    return self._lastTxCountPerFeeLevel[feeIndex] + self._txToBeAdded[feeIndex] 
  
  def getAverageFee(self, txsWithNumGreaterThanOne): # txsWithNumGreaterThanOne: transactions with tx.num > 1, temporary solution
    tx_count_per_fee_level = self._getFullTxCountPerFeeLevel(txsWithNumGreaterThanOne)
    total_tx_count = sum(tx_count_per_fee_level)
    acc = 0
    i = 0
    while i < len(tx_count_per_fee_level):
      acc = acc + (fee_ranges[i] * tx_count_per_fee_level[i])
      i = i + 1
    avg_fee = acc / total_tx_count
    average_index = self._findIndexOfFeeInRanges(avg_fee)
    return average_index, avg_fee
  
  def _getFullTxCountPerFeeLevel(self, txsWithNumGreaterThanOne):
    full_tx_count_per_fee_level = [0] * len(fee_ranges)
    
    for i in range(len(fee_ranges)):
      full_tx_count_per_fee_level[i] += txsWithNumGreaterThanOne[i] + self._lastTxCountPerFeeLevel[i] + self._txToBeAdded[i]
      if len(self._userTxsPerFeeLevel[i]) > 0:
        full_tx_count_per_fee_level[i] += (len(self._userTxsPerFeeLevel[i]) - self._noneTxsPerFeeLevel[i])
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

    self._txToBeAdded[fee_index] = max(self._txToBeAdded[fee_index] - amount, 0)

    for tx in list(filter(lambda tx: tx is not None, self._userTxsPerFeeLevel[fee_index])):
      tx.txWithSameFee = max(tx.txWithSameFee - amount, 0)    
  
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

  def run(self):
    snapshot = self._mempoolData[self._currentMempoolIndex]
    self._currentMempoolIndex += 1

    timestamp = snapshot[0]
    tx_count_per_fee_level = snapshot[1]
    total_tx_count = sum(tx_count_per_fee_level)

    if self._lastTotalTxCount is None and self._lastTxCountPerFeeLevel is None:
      self._lastTxCountPerFeeLevel = tx_count_per_fee_level
      self._lastTotalTxCount = total_tx_count
      return

    # "Problematic" intervals are intervals in which probably the node of the owner of the website that gives the dataset
    # went offline for sometime
    is_in_problematic_interval = self._isInProblematicInterval(timestamp)

    if total_tx_count < self._lastTotalTxCount and not is_in_problematic_interval:
      # New Block
      
      #print(f"[INFO] New Block (#{self._firstHeight + self._blocksCounter}) detected")

      # On new block, we compute the number of transactions with a fee that is higher than LN txs
      # If this number is higher than the number of transactions in the block, no LN txs are confirmed in this block.
      # Otherwise, some LN txs could be included in the block, and we must check their current "position" in the mempool
      # at their fee level, i.e. how many txs there are in the same fee level that were submitted before them.

      self._blocksCounter += 1
      
      num_tx_in_block = self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + self._blocksCounter) - 1]["n_transactions"]
      
      # As said before, LN txs actually "replace" standard txs that would have been removed from the mempool
      # without LN txs, therefore they must be re-added and considered for future blocks.
      amount_tx_to_be_added = 0
      starting_index_tx_to_be_added = 0

      # We find the higher fee in LN transactions
      highest_user_fee_index = 0
      i = len(fee_ranges) - 1
      while i >= 0:
        if len(self._userTxsPerFeeLevel[i]) > 0:
          highest_user_fee_index = i
          break
        i -= 1

      index = len(self._lastTxCountPerFeeLevel) - 1
      tx_with_higher_fee = 0

      # Now we confirm transactions that have an higher fee than our LN txs
      while index > highest_user_fee_index and tx_with_higher_fee < num_tx_in_block:
        tmp = tx_with_higher_fee
        tx_with_higher_fee = tx_with_higher_fee + self._lastTxCountPerFeeLevel[index] + self._txToBeAdded[index]

        # Here we don't call decreaseTxWithSameFee because there are no LN txs in this fee level
        # by construction (fee_index > highest_ln_fee_index)

        self._txToBeAdded[index] = max(self._txToBeAdded[index] - (num_tx_in_block - tmp), 0)
        index -= 1

      tx_to_be_confirmed = num_tx_in_block - tx_with_higher_fee

      if tx_to_be_confirmed > 0:

        # We put None placeholder values in the `ln_txs_per_fee_level` array to remove confirmed ln txs after
        # all the txs that are included in the block are computed, therefore the None txs must not be taken into
        # consideration when we compute the average fee for new victim transactions. Using `filter` on None values
        # slows down too much the simulation, thus it's more efficient to keep track of the number of None values
        # for each fee level and then subtracting their number when needed.
        
        self._noneTxsPerFeeLevel = [0] * len(fee_ranges)

        # There is still "space" for more transactions in the block
    
        fee_index = highest_user_fee_index
        
        while fee_index >= 0 and tx_to_be_confirmed > 0:
            
          user_txs = self._userTxsPerFeeLevel[fee_index]

          if len(user_txs) > 0: # If there are LN txs in this fee level
            tx_index = 0

            while tx_index < len(user_txs) and tx_to_be_confirmed > 0:
              tx = self._userTxsPerFeeLevel[fee_index][tx_index]
              
              # The "position" of txs in the mempool is modified
              if tx.txWithSameFee >= tx_to_be_confirmed:
                self._decreaseTxWithSameFee(fee_index, tx_to_be_confirmed)
                tx_to_be_confirmed = 0
              else:
                if tx.txWithSameFee > 0:
                  tx_to_be_confirmed -= tx.txWithSameFee
                  self._decreaseTxWithSameFee(fee_index, tx.txWithSameFee)
              
              if tx.num > 1:
                tmp = tx.num
                tx.num = max(tmp - tx_to_be_confirmed, 0)
                num_attacker_confirmed_txs = tmp - tx.num
                tx_to_be_confirmed -= num_attacker_confirmed_txs
                amount_tx_to_be_added += num_attacker_confirmed_txs
                starting_index_tx_to_be_added = tx.feeIndex
                self._confirmedTxCount += num_attacker_confirmed_txs
                if tx.num == 0:
                  tx.confirmed = True
                  tx.confirmedBlockNumber = self._blocksCounter
                  self._userTxsPerFeeLevel[fee_index][tx_index] = None
                  self._noneTxsPerFeeLevel[fee_index] += 1
              else:
                tx.confirmed = True
                tx.confirmedBlockNumber = self._blocksCounter
                tx_to_be_confirmed -= 1                        
                amount_tx_to_be_added += 1
                starting_index_tx_to_be_added = tx.feeIndex 
                self._userTxsPerFeeLevel[tx.feeIndex][tx_index] = None
                self._noneTxsPerFeeLevel[tx.feeIndex] += 1
                self._confirmedTxCount += 1

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

      if self._dynamic and self._blocksCounter % self._step == 0:
        tx_to_be_removed = []
        tx_to_be_added_dynamically = []

        for i in range(len(fee_ranges)):
            empty_array = []
            tx_to_be_removed.append(empty_array)

        for i in range(len(fee_ranges)):
            empty_array = []
            tx_to_be_added_dynamically.append(empty_array)    

        for fee_index in range(len(self._userTxsPerFeeLevel)):
            for tx_index in range(len(self._userTxsPerFeeLevel[fee_index])):
                tx = self._userTxsPerFeeLevel[fee_index][tx_index]
                if tx.confirmed or not tx.dynamic: #tx.isAttacker or tx.attackerTxConfirmedBlockNumber == self._blocksCounter: # TODO: should attacker use RBF?
                    continue
                new_fee = tx.currentFee * self._beta
                tx.currentFee = new_fee
                new_fee_index = self._findIndexOfFeeInRanges(new_fee)

                if new_fee_index != tx.feeIndex:
                    tx.feeIndex = new_fee_index
                    tx.txWithSameFee = tx_count_per_fee_level[new_fee_index] + self._txToBeAdded[new_fee_index] 
                    self._userTxsPerFeeLevel[fee_index][tx_index] = None
                    tx_to_be_removed[fee_index].append(tx_index)
                    tx_to_be_added_dynamically[new_fee_index].append(tx)

        for i in range(len(self._userTxsPerFeeLevel)):
            self._userTxsPerFeeLevel[i] = list(filter(lambda tx: tx is not None, self._userTxsPerFeeLevel[i]))

        for txs in tx_to_be_added_dynamically:
            for tx in txs:
              self._userTxsPerFeeLevel[tx.feeIndex].append(tx)

    self._lastTotalTxCount = total_tx_count
    self._lastTxCountPerFeeLevel = tx_count_per_fee_level