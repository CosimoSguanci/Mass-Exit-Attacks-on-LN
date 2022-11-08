from model.Transaction import Transaction

class MassExitTransaction(Transaction):
  # _isAttacker = False
  # _attackerTxConfirmedBlockNumber = -1
  
  def __init__(self, isAttacker, num, isDynamic):
    super().__init__(num, isDynamic)
    self._isAttacker = isAttacker
    self._attackerTxConfirmedBlockNumber = -1

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