class Transaction:
  # _submitted = False
  # _confirmed = False
  # _confirmedBlockNumber = -1
  # _feeIndex = -1
  # _currentFee = -1
  # _txWithSameFee = -1
  # _num = 1
  # _dynamic = False
  
  def __init__(self, num, isDynamic):
    self._submitted = False
    self._confirmed = False
    self._confirmedBlockNumber = -1
    self._feeIndex = -1
    self._currentFee = -1
    self._txWithSameFee = -1
    self._num = num
    self._dynamic = isDynamic

  @property
  def submitted(self):
    return self._submitted
    
  @submitted.setter
  def submitted(self, submitted):
    self._submitted = submitted

  @property
  def confirmed(self):
    return self._confirmed
    
  @confirmed.setter
  def confirmed(self, confirmed):
    self._confirmed = confirmed
    
  #@property
  #def submittedBlockNumber(self):
    #return self._submittedBlockNumber
    
  #@submittedBlockNumber.setter
  #def submittedBlockNumber(self, submittedBlockNumber):
    #self._submittedBlockNumber = submittedBlockNumber    

  @property
  def confirmedBlockNumber(self):
    return self._confirmedBlockNumber
    
  @confirmedBlockNumber.setter
  def confirmedBlockNumber(self, confirmedBlockNumber):
    self._confirmedBlockNumber = confirmedBlockNumber

  @property
  def feeIndex(self):
    return self._feeIndex
    
  @feeIndex.setter
  def feeIndex(self, feeIndex):
    self._feeIndex = feeIndex    

  @property
  def currentFee(self):
    return self._currentFee
    
  @currentFee.setter
  def currentFee(self, currentFee):
    self._currentFee = currentFee

  @property
  def txWithSameFee(self):
    return self._txWithSameFee
    
  @txWithSameFee.setter
  def txWithSameFee(self, txWithSameFee):
    self._txWithSameFee = txWithSameFee
    
  @property
  def num(self):
    return self._num
    
  @num.setter
  def num(self, num):
    self._num = num
    
  @property
  def dynamic(self):
    return self._dynamic
    
  @dynamic.setter
  def dynamic(self, dynamic):
    self._dynamic = dynamic