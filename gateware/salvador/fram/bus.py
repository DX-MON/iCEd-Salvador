from nmigen import *

class Bus(Elaboratable):
	def __init__(self, *, resource):
		self._bus = resource
		self.cs = Signal()
		self.copi = Signal(8)
		self.copi_oe = Signal(reset = 1)
		self.cipo = Signal(8)
		self.begin = Signal()
		self.complete = Signal()

	def elaborate(self, platform) -> Module:
		m = Module()
		bus = self._bus
		data = Signal.like(self.copi)
		bitCounter = Signal(range(8))

		m.d.comb += [
			self.complete.eq(0),
			bus.cs.o.eq(self.cs),
			bus.copi.oe.eq(self.copi_oe),
		]

		with m.FSM(name = 'spi-fsm'):
			with m.State('IDLE'):
				with m.If(self.begin):
					m.d.sync += bitCounter.eq(7)
					m.next = 'SHIFT-START'
			with m.State('SHIFT-START'):
				m.d.sync += data.eq(self.copi)
				m.next = 'SHIFT-L'
			with m.State('SHIFT-L'):
				m.d.sync += [
					bus.clk.o.eq(0),
					bus.copi.o.eq(data[7]),
					data.eq(data.shift_left(1)),
					bitCounter.eq(bitCounter - 1),
				]
				m.next = 'SHIFT-H'
			with m.State('SHIFT-H'):
				m.d.sync += [
					bus.clk.o.eq(1),
					self.cipo.eq(self.cipo.shift_right(1)),
					self.cipo[7].eq(bus.cipo.i),
				]
				with m.If(bitCounter == 0):
					m.d.comb += self.complete.eq(1)
					m.next = 'IDLE'
				with m.Else():
					m.next = 'SHIFT-L'
		return m
