import logging
import abc

fee_ranges =  [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 17, 20, 25, 30, 40, 50, 60, 70, 80, 100, 120, 140, 170, 200, 250, 300, 400, 500, 600, 700, 800, 1000, 1200, 1400, 1700, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 10000]

class Simulation():

  # _dynamic = False
  # _step = -1
  # _beta = -1                     
  # _mempoolData = None
  # _blocksData = None
  # _firstHeight = -1 # in our blocks dataset
  # _firstBlockHeightOfSimulation = -1
  # _blocksCounter = 0
  # _lastTxCountPerFeeLevel = None 
  # _problematicIntervals = []
  # _lastTotalTxCount = -1

  def __init__(self, mempoolData, blocksData, isDynamic, firstBlockHeightOfSimulation, problematicIntervals, step, beta):
    self._dynamic = isDynamic
    self._mempoolData = mempoolData
    self._blocksData = blocksData
    self._firstHeight = self._blocksData[0]["height"]
    self._firstBlockHeightOfSimulation = firstBlockHeightOfSimulation
    self._problematicIntervals = problematicIntervals
    self._step = step
    self._beta = beta
    self._blocksCounter = 0
    self._lastTxCountPerFeeLevel = None 
    self._lastTotalTxCount = -1

  @property
  def blocksCounter(self):
    return self._blocksCounter
  
  @abc.abstractmethod
  def run(self):
    return

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

  def _findIndexOfFeeInRanges(self, fee):
    fee_index = 0
    i = 1

    while i < len(fee_ranges):
      if fee_ranges[i-1] <= fee and fee < fee_ranges[i]:
        fee_index = i-1
        return fee_index
      i = i + 1

    return len(fee_ranges) - 1 # maximum fee index

  def _isInProblematicInterval(self, timestamp):
    for interval in self._problematicIntervals:
      if timestamp >= interval[0] and timestamp < interval[1]:
        return True
    return False
