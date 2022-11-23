from simulation.Simulation import Simulation
from datetime import datetime

class SimpleModeSimulation(Simulation):

  def __init__(self, mempoolData, blocksData, isDynamic, useHistoricalBlocksData, firstBlockHeightOfSimulation, problematicIntervals, step, beta, remainingTxs, feeIndexInRanges):
    super().__init__(mempoolData, blocksData, isDynamic, useHistoricalBlocksData, firstBlockHeightOfSimulation, problematicIntervals, step, beta)
    self._remainingTxs = remainingTxs
    self._feeIndexInRanges = feeIndexInRanges
    self._currentFee = self._getAllFeeRanges()[feeIndexInRanges]
    self._firstBlockDone = False
    self._tx_distribution = []
  
  def _processBlock(self, tx_count_per_fee_level, num_tx_in_block):
    
    txs_with_higher_fee = [0] * len(self._getAllFeeRanges()) # Transactions that have an higher fee than users' txs
    index = self._feeIndexInRanges + 1
    while index < len(self._lastTxCountPerFeeLevel):
        txs_with_higher_fee[index] = self._lastTxCountPerFeeLevel[index]
        index = index + 1

    remaining_tx_in_block = max(num_tx_in_block - sum(txs_with_higher_fee), 0)   
    
    confirmedTxs = num_tx_in_block - remaining_tx_in_block
    index = len(self._lastTxCountPerFeeLevel) - 1
    while confirmedTxs > 0:
        tmp = self._lastTxCountPerFeeLevel[index]
        newTxCount = max(self._lastTxCountPerFeeLevel[index] - confirmedTxs, 0)
        self._lastTxCountPerFeeLevel[index] = newTxCount 
        confirmedTxs -= (tmp - newTxCount)
        index -= 1

    if remaining_tx_in_block > 0: 
        
        number_of_confirmed_tx_in_this_fee_level = remaining_tx_in_block

        if self._txSameFeeLevel >= number_of_confirmed_tx_in_this_fee_level:
            self._txSameFeeLevel -= number_of_confirmed_tx_in_this_fee_level
        else:
            if self._txSameFeeLevel > 0:
                number_of_confirmed_tx_in_this_fee_level -= self._txSameFeeLevel
                self._txSameFeeLevel = 0
        
            # In this case, differently from the other type of attack, we dont have to take into account
            # the fact that the LN transactions that we are monitoring are "replacing" some other transactions that
            # are removed from the mempool in the dataset, because they would be confirmed after all the LN txs (LN txs in this
            # case are considered as simultaneously submitted, they are "grouped" together), therefore we are not interested
            # in keeping track of them.

            self._remainingTxs = max(self._remainingTxs - remaining_tx_in_block, 0)

    dynamicFeeIncrease = self._dynamic and self._blocksCounter % self._step == 0
    if dynamicFeeIncrease:
        new_fee = self._currentFee * self._beta
        oldIndex = self._feeIndexInRanges
        self._feeIndexInRanges = self._findIndexOfFeeInRanges(new_fee)
        self._currentFee = new_fee
        if self._feeIndexInRanges != oldIndex:
            self._txSameFeeLevel = tx_count_per_fee_level[self._feeIndexInRanges]
    
    self._tx_distribution.append(self._remainingTxs) # should do two appends in case of 2 blocks detected
 

  def run(self):
    for snapshot in self._mempoolData:
        self._confirmedTxs = [0] * len(self._getAllFeeRanges())
        timestamp = snapshot[0]
        tx_count_per_fee_level = snapshot[1].copy() # Array that contains, for each fee level in `fee_ranges`, the corresponding number of transactions currently in the mempool
        total_tx_count = sum(tx_count_per_fee_level)

        if self._lastTotalTxCount == -1 and self._lastTxCountPerFeeLevel is None:
            # First snapshot
            self._lastTotalTxCount = total_tx_count
            self._lastTxCountPerFeeLevel = tx_count_per_fee_level.copy()
            self._txSameFeeLevel = tx_count_per_fee_level[self._feeIndexInRanges] # Keeps the number of txs in the same fee range which have more priority (because they were submitted earlier)
        else:
            is_in_problematic_interval = self._isInProblematicInterval(timestamp)
            if not is_in_problematic_interval and total_tx_count < self._lastTotalTxCount:
                # New Block(s) detected
                if self._firstBlockDone:
                    self._blocksCounter += 1
                else:
                    self._firstBlockDone = True  
                
                #print(f"[INFO] New Block (#{self._firstBlockHeightOfSimulation + self._blocksCounter}) detected at time {datetime.fromtimestamp(timestamp)}")
                num_tx_first_block = self._getTransactionsInNextBlock() #self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + self._blocksCounter)]["n_transactions"]
                tx_diff = self._lastTotalTxCount - total_tx_count
                first_block_timestamp = self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + self._blocksCounter)]["timestamp"]
                second_block_timestamp = self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + self._blocksCounter) + 1]["timestamp"]
                firstBlockTime = datetime.fromtimestamp(first_block_timestamp)
                secondBlockTime = datetime.fromtimestamp(second_block_timestamp)
                t_diff = (secondBlockTime - firstBlockTime).total_seconds()
                is_two_blocks = (tx_diff >= num_tx_first_block + 1000) and (t_diff < 60)  #(tx_diff > num_tx_first_block) and (t_diff < 60)  

                self._processBlock(tx_count_per_fee_level, num_tx_first_block) 
                if is_two_blocks:
                    self._blocksCounter += 1
                    #print(f"[INFO] New Block (#{self._firstBlockHeightOfSimulation + self._blocksCounter}) detected at time {datetime.fromtimestamp(timestamp)}")
                    num_tx_second_block = self._getTransactionsInNextBlock() #self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + self._blocksCounter) + 1]["n_transactions"]
                    self._processBlock(tx_count_per_fee_level, num_tx_second_block) 
                
            self._lastTotalTxCount = total_tx_count
            self._lastTxCountPerFeeLevel = tx_count_per_fee_level.copy()

        if self._remainingTxs <= 0: 
            return self._blocksCounter, self._tx_distribution 
    
    print("[WARN] Couldn't finish within the simulation time frame")       
    raise Exception("Time frame expired before confirming all transactions") 
