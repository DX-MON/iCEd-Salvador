from nmigen import *
from .manchester import *

class Serial(Elaboratable):
	def __init__(self, *, baudRate = 1200):
		self.rx = Signal()
		self.tx = Signal()
		self.dataIn = Signal(8)
		self.dataOut = Signal(16)
		self.dataAvailable = Signal()
		self.error = Signal()
		self._bitRate = baudRate * 2

	def elaborate(self, platform):
		m = Module()
		timerCount = int(platform.default_clk_frequency) // self._bitRate
		timerWidth = range(timerCount)
		timer = Signal(timerWidth)
		timerEnabled = Signal()

		with m.If(timerEnabled):
			with m.If(timer == (timerCount - 1)):
				m.d.sync += timer.eq(0)
			with m.Else():
				m.d.sync += timer.eq(timer + 1)
		with m.Else():
			m.d.sync += timer.eq(0)

		m.submodules.encoder = encoder = ManchesterEncoder()
		m.submodules.decoder = decoder = ManchesterDecoder()

		step = Signal()
		cycle = Signal()

		m.d.comb += [
			step.eq((timer == 0) & timerEnabled),
			self.dataAvailable.eq(0),

			encoder.step.eq(step),
			self.tx.eq(encoder.dataOut),

			decoder.step.eq(step),
			decoder.dataIn.eq(self.rx),
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

		with m.FSM(name = "rx-fsm"):
			with m.State("IDLE"):
				with m.If(startStrobe):
					m.d.sync += [
						timerEnabled.eq(1),
						cycle.eq(0),
					]
					m.next = "START"
				with m.Else():
					m.d.sync += timerEnabled.eq(0)
			with m.State("START"):
				with m.If(step):
					m.d.sync += cycle.eq(cycle ^ 1)
				with m.If(step & cycle):
					m.next = "START-CHECK"
			with m.State("START-CHECK"):
				with m.If(decoder.valid):
					m.d.sync += [
						dataValid.eq(1),
						dataRXCount.eq(0),
					]
					m.next = "SHIFT"
				with m.Else():
					m.next = "IDLE"
			with m.State("SHIFT"):
				with m.If(step):
					m.d.sync += cycle.eq(cycle ^ 1)
				with m.If(step & cycle):
					m.next = "SHIFT-CHECK"
			with m.State("SHIFT-CHECK"):
				m.d.sync += [
					dataRX.eq(Cat(decoder.dataOut , dataRX[:-1])),
					dataRXCount.eq(dataRXCount + 1),
				]
				with m.If(~decoder.valid):
					m.d.sync += dataValid.eq(0)
				with m.If(dataRXCount == 15):
					m.d.sync += [
						decoder.bypass.eq(1),
						dataRXStopCount.eq(0),
					]
					m.next = "STOP"
				with m.Else():
					m.next = "SHIFT"
			with m.State("STOP"):
				with m.If(step):
					m.d.sync += cycle.eq(cycle ^ 1)
				with m.If(step & cycle):
					m.d.sync += dataRXStopCount.eq(dataRXStopCount + 1)
					with m.If(~decoder.valid):
						m.d.sync == dataValid.eq(0)
					with m.If(dataRXStopCount == 1):
						with m.If(~dataRXError):
							m.d.sync += self.dataOut.eq(dataRX)
						m.d.sync += self.error.eq(dataRXError)
						m.d.comb += self.dataAvailable.eq(1)
						m.next = "IDLE"
		m.d.comb += dataRXError.eq(dataValid & (~decoder.valid))
		return m
