from simulation.Simulation import Simulation
import logging

class SimpleModeSimulation(Simulation):
  # Only used in simple mode
  _feeIndexInRanges = -1
  _currentFee = -1
  _remainingTxs = -1

  def __init__(self, mempoolData, blocksData, isDynamic, firstBlockHeightOfSimulation, problematicIntervals, step, beta, remainingTxs, feeIndexInRanges):
    super().__init__(mempoolData, blocksData, isDynamic, firstBlockHeightOfSimulation, problematicIntervals, step, beta)
    self._remainingTxs = remainingTxs
    self._feeIndexInRanges = feeIndexInRanges

  def run(self):
    tx_distribution = []
    initial_tx_with_same_fee = self._mempoolData[0][1][self._feeIndexInRanges]
    for snapshot in self._mempoolData:
        timestamp = snapshot[0]
        tx_count_per_fee_level = snapshot[1] # Array that contains, for each fee level in `fee_ranges`, the corresponding number of transactions currently in the mempool
        total_tx_count = sum(tx_count_per_fee_level)

        if self._lastTotalTxCount == -1 and self._lastTxCountPerFeeLevel is None:
            # First snapshot
            self._lastTotalTxCount = total_tx_count
            self._lastTxCountPerFeeLevel = tx_count_per_fee_level
        else:
            is_in_problematic_interval = self._isInProblematicInterval(timestamp)
            if not is_in_problematic_interval and total_tx_count < self._lastTotalTxCount:

                logging.info(f"[INFO] New Block (#{self._firstHeight + self._blocksCounter}) detected")
                
                # New Block detected
                self._blocksCounter += 1
                
                # `firstBlockHeightOfSimulation` is the first block that we will encounter in our simulation (must be manually found using a block explorer)
                # `first_height` is the first blocck number in our blocks dataset
                # These two parameter could differ based on the collected block dataset and the time frame taken into consideration for the simulation.
                num_tx_in_block = self._blocksData[(self._firstBlockHeightOfSimulation - self._firstHeight + self._blocksCounter) - 1]["n_transactions"]
                
                tx_with_higher_fee = 0 # Number of transactions that have an higher fee than the closing channel transactions
                index = self._feeIndexInRanges + 1
                while index < len(tx_count_per_fee_level):
                    tx_with_higher_fee = tx_with_higher_fee + self._lastTxCountPerFeeLevel[index]
                    index = index + 1

                if num_tx_in_block > tx_with_higher_fee: 
                    
                    # The new block can contain transactions with the level of fee we are considering for closing channel transactions
                    
                    number_of_confirmed_tx_in_this_fee_level = num_tx_in_block - tx_with_higher_fee 

                    if initial_tx_with_same_fee >= number_of_confirmed_tx_in_this_fee_level:
                        initial_tx_with_same_fee -= number_of_confirmed_tx_in_this_fee_level
                    else:
                        if initial_tx_with_same_fee > 0:
                            number_of_confirmed_tx_in_this_fee_level -= initial_tx_with_same_fee
                            initial_tx_with_same_fee = 0

                        # In this case, differently from the other type of attack, we dont have to take into account
                        # the fact that the LN transactions that we are monitoring are "replacing" some other transactions that
                        # are removed from the mempool in the dataset, because they would be confirmed after all the LN txs (LN txs in this
                        # case are considered as simultaneously submitted, they are "grouped" together), therefore we are not interested
                        # in keeping track of them.

                        self._remainingTxs = max(self._remainingTxs - number_of_confirmed_tx_in_this_fee_level, 0)

                if self._dynamic and self._blocksCounter % self._step == 0:
                    new_fee = self._currentFee * self._beta
                    self._feeIndexInRanges = self._findIndexOfFeeInRanges(new_fee)
                    self._currentFee = new_fee

                tx_distribution.append(self._remainingTxs)

            self._lastTotalTxCount = total_tx_count
            self._lastTxCountPerFeeLevel = tx_count_per_fee_level 

        if self._remainingTxs <= 0: 
            return self._blocksCounter, tx_distribution 
    
    logging.warn("[WARN] Couldn't finish within the simulation time frame")       
    raise Exception("Time frame expired before confirming all transactions") 
