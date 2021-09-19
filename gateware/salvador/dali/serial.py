from nmigen import *
from .manchester import *

class Serial(Elaboratable):
	def __init__(self, *, baudRate = 1200):
		self.rx = Signal()
		self.tx = Signal()
		self.dataIn = Signal(8)
		self.dataSend = Signal()
		self.sendComplete = Signal()
		self.dataOut = Signal(16)
		self.dataAvailable = Signal()
		self.error = Signal()
		self._bitRate = baudRate * 2

	def elaborate(self, platform):
		m = Module()
		timerCount = int(platform.default_clk_frequency) // self._bitRate
		timerWidth = range(timerCount)
		rxTimer = Signal(timerWidth)
		txTimer = Signal(timerWidth)
		rxTimerEnabled = Signal()
		txTimerEnabled = Signal()

		with m.If(rxTimerEnabled):
			with m.If(rxTimer == (timerCount - 1)):
				m.d.sync += rxTimer.eq(0)
			with m.Else():
				m.d.sync += rxTimer.eq(rxTimer + 1)
		with m.Else():
			m.d.sync += rxTimer.eq(0)

		with m.If(txTimerEnabled):
			with m.If(txTimer == (timerCount - 1)):
				m.d.sync += txTimer.eq(0)
			with m.Else():
				m.d.sync += txTimer.eq(txTimer + 1)
		with m.Else():
			m.d.sync += txTimer.eq(0)

		m.submodules.encoder = encoder = ManchesterEncoder()
		m.submodules.decoder = decoder = ManchesterDecoder()

		rxStep = Signal()
		rxCycle = Signal()
		txStep = Signal()
		txCycle = Signal()

		m.d.comb += [
			rxStep.eq((rxTimer == 0) & rxTimerEnabled),
			self.dataAvailable.eq(0),
			txStep.eq((txTimer == 0) & txTimerEnabled),
			self.sendComplete.eq(0),

			decoder.step.eq(rxStep),
			decoder.dataIn.eq(self.rx),

			encoder.step.eq(txStep),
			self.tx.eq(encoder.dataOut),
		]

		rxDelayed = Signal()
		startStrobe = Signal()
		m.d.sync += rxDelayed.eq(self.rx)
		m.d.comb += startStrobe.eq(rxDelayed & ~self.rx)

		dataValid = Signal()
		dataRX = Signal.like(self.dataOut)
		dataRXCount = Signal(range(16))
		dataRXStopCount = Signal(range(2))
		dataRXError = Signal()

		with m.FSM(name = 'rx-fsm'):
			# Wait for data on the rx line
			with m.State('IDLE'):
				with m.If(startStrobe):
					# We've seen the start bit condition, start the rx timer
					# and reset the cycle toggle + bypass mode
					m.d.sync += [
						rxTimerEnabled.eq(1),
						rxCycle.eq(0),
						decoder.bypass.eq(0),
					]
					m.next = 'START'
				with m.Else():
					# Ensure the rx timer is off (resets it to 0) otherwise
					m.d.sync += rxTimerEnabled.eq(0)
			# We saw the start condition, wait half a bit time to check it
			with m.State('START'):
				with m.If(rxStep):
					m.d.sync += rxCycle.eq(rxCycle ^ 1)
				with m.If(rxStep & rxCycle):
					m.next = 'START-CHECK'
			# Retiming and decoder check state for the start bit (first half)
			with m.State('START-CHECK'):
				with m.If(decoder.valid):
					m.d.sync += [
						dataValid.eq(1),
						dataRXCount.eq(0),
					]
					m.next = 'SHIFT'
				with m.Else():
					m.next = 'IDLE'
			# Data shift state
			with m.State('SHIFT'):
				with m.If(rxStep):
					m.d.sync += rxCycle.eq(rxCycle ^ 1)
				with m.If(rxStep & rxCycle):
					# When we get to the first half of the cycle for the next bit,
					# we know the current one is good and can be stored
					m.next = 'SHIFT-CHECK'
			# Retiming and decoder check + data store state
			with m.State('SHIFT-CHECK'):
				# Store the value of the *previous* bit
				m.d.sync += [
					dataRX.eq(Cat(decoder.dataOut , dataRX[:-1])),
					dataRXCount.eq(dataRXCount + 1),
				]
				# Check if the decoder state indicates an error (invalidate if true)
				with m.If(~decoder.valid):
					m.d.sync += dataValid.eq(0)
				# If we timed in all the bits then put the decoder into bypass and look for the stop bits
				# (This state covers the first half of the first stop bit)
				with m.If(dataRXCount == 15):
					m.d.sync += [
						decoder.bypass.eq(1),
						dataRXStopCount.eq(0),
					]
					m.next = 'STOP'
				# Next bit please
				with m.Else():
					m.next = 'SHIFT'
			# Stop bit checking
			with m.State('STOP'):
				with m.If(rxStep):
					m.d.sync += rxCycle.eq(rxCycle ^ 1)
				with m.If(rxStep & rxCycle):
					# If we've seen the second half of the current stop bit
					m.d.sync += dataRXStopCount.eq(dataRXStopCount + 1)
					# Make sure things are still valid (invalidate if not)
					with m.If(~decoder.valid):
						m.d.sync == dataValid.eq(0)
					# If we've seen both stop bits
					with m.If(dataRXStopCount == 1):
						# Make the error state and received data are presented up
						m.d.sync += [
							self.error.eq(dataRXError),
							self.dataOut.eq(dataRX),
						]
						# And signal that we've made data available
						m.d.comb += self.dataAvailable.eq(1)
						m.next = 'IDLE'
		m.d.comb += dataRXError.eq(dataValid & (~decoder.valid))

		dataTX = Signal.like(self.dataIn)
		dataTXCount = Signal(range(8))
		dataTXStopCount = Signal(range(2))

		with m.FSM(name = 'tx-fsm'):
			with m.State('IDLE'):
				with m.If(self.dataSend):
					m.d.sync += [
						txTimerEnabled.eq(1),
						txCycle.eq(0),
						encoder.bypass.eq(0),
						encoder.dataIn.eq(0),
					]
					m.next = 'START'
				with m.Else():
					m.d.sync += txTimerEnabled.eq(0)
			with m.State('START'):
				with m.If(txStep):
					m.d.sync += txCycle.eq(txCycle ^ 1)
				with m.If(txStep & txCycle):
					m.d.sync += dataTX.eq(self.dataIn)
					m.next = 'START-CHECK'
			with m.State('START-CHECK'):
				m.d.sync += [
					dataTXCount.eq(0),
					encoder.dataIn.eq(dataTX[7]),
				]
				m.next = 'SHIFT'
			with m.State('SHIFT'):
				with m.If(txStep):
					m.d.sync += txCycle.eq(txCycle ^ 1)
				with m.If(txStep & txCycle):
					m.d.sync += dataTX.eq(dataTX.shift_left(1)),
					m.next = 'SHIFT-CHECK'
			with m.State('SHIFT-CHECK'):
				m.d.sync += dataTXCount.eq(dataTXCount + 1)
				with m.If(dataTXCount == 7):
					m.d.sync += [
						encoder.bypass.eq(1),
						encoder.dataIn.eq(1),
						dataTXStopCount.eq(0),
					]
					m.next = 'STOP'
				with m.Else():
					m.d.sync += encoder.dataIn.eq(dataTX[7]),
					m.next = 'SHIFT'
			with m.State('STOP'):
				with m.If(txStep):
					m.d.sync += txCycle.eq(txCycle ^ 1)
				with m.If(txStep & txCycle):
					m.d.sync += dataTXStopCount.eq(dataTXStopCount + 1)
					with m.If(dataTXStopCount == 1):
						m.d.comb += self.sendComplete.eq(1)
						m.next = 'IDLE'
		return m
