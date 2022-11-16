from model.Transaction import Transaction

class MassExitTransaction(Transaction):
  # _isAttacker = False
  # _attackerTxConfirmedBlockNumber = -1
  
  def __init__(self, isAttacker, num, isDynamic):
    super().__init__(num, isDynamic)
    self._isAttacker = isAttacker
    self._attackerTxConfirmedBlockNumber = -1
    self._penaltyTxIndex = -1 # if isAttacker and is second attacker tx

  @property
  def isAttacker(self):
    return self._isAttacker
    
  @isAttacker.setter
  def isAttacker(self, isAttacker):
    self._isAttacker = isAttacker

  @property
  def attackerTxConfirmedBlockNumber(self):
    return self._attackerTxConfirmedBlockNumber
    
  @attackerTxConfirmedBlockNumber.setter
  def attackerTxConfirmedBlockNumber(self, attackerTxConfirmedBlockNumber):
    self._attackerTxConfirmedBlockNumber = attackerTxConfirmedBlockNumber

  @property
  def penaltyTxIndex(self):
    return self._penaltyTxIndex
    
  @penaltyTxIndex.setter
  def penaltyTxIndex(self, penaltyTxIndex):
    self._penaltyTxIndex = penaltyTxIndex