from nmigen import *

__all__ = ('ManchesterEncoder', 'ManchesterDecoder')

class ManchesterEncoder(Elaboratable):
	def __init__(self):
		self.dataIn = Signal()
		self.step = Signal()
		self.dataOut = Signal()
		self.bypass = Signal()

	def elaborate(self, platform):
		m = Module()

		data = Signal()
		cycle = Signal()

		with m.If(self.step):
			with m.If(self.bypass):
				m.d.sync += [
					self.dataOut.eq(self.dataIn),
					cycle.eq(0),
				]
			with m.Elif(~cycle):
				m.d.sync += [
					data.eq(self.dataIn),
					self.dataOut.eq(self.dataIn),
					cycle.eq(1),
				]
			with m.Else():
				m.d.sync += [
					self.dataOut.eq(~data),
					cycle.eq(0),
				]

		return m

class ManchesterDecoder(Elaboratable):
	def __init__(self):
		self.dataIn = Signal()
		self.step = Signal()
		self.dataOut = Signal()
		self.valid = Signal()
		self.bypass = Signal()

	def elaborate(self, platform):
		m = Module()

		data = Signal()
		cycle = Signal()

		with m.If(self.step):
			with m.If(~cycle):
				m.d.sync += [
					data.eq(self.dataIn),
					cycle.eq(1),
				]
			with m.Elif(~self.bypass):
				m.d.sync += [
					self.dataOut.eq(data),
					self.valid.eq(data == ~self.dataIn),
					cycle.eq(0),
				]
			with m.Else():
				m.d.sync += [
					self.dataOut.eq(data),
					self.valid.eq(data == self.dataIn),
					cycle.eq(0),
				]

		return m
