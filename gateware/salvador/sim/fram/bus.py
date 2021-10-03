from arachne.core.sim import sim_case
from nmigen import Elaboratable, Module, Signal, ResetSignal, Record
from nmigen.hdl.rec import DIR_FANIN, DIR_FANOUT
from nmigen.sim import *

from ...fram.bus import *

__all__ = (
	'transactions',
)

bus = Record(
	layout = (
		('cs', [
			('o', 1, DIR_FANOUT),
		]),
		('clk', [
			('o', 1, DIR_FANOUT),
		]),
		('copi', [
			('o', 1, DIR_FANOUT),
			('oe', 1, DIR_FANOUT),
		]),
		('cipo', [
			('i', 1, DIR_FANIN),
		]),
	)
)

class DUT(Elaboratable):
	def __init__(self, *, resource):
		self._dut = Bus(resource = resource)
		self._bus = self._dut._bus
		self.cs = self._dut.cs
		self.copi = self._dut.copi
		self.copi_oe = self._dut.copi_oe
		self.cipo = self._dut.cipo
		self.begin = self._dut.begin
		self.complete = self._dut.complete
		self.reset = Signal()

	def elaborate(self, platform) -> Module:
		m = Module()
		m.submodules.bus = self._dut
		m.d.comb += ResetSignal().eq(self.reset)
		return m

def performIO(*, bus, dut, dataOut = None, dataIn = None):
	yield Settle()
	assert (yield dut.begin) == 0
	if dataOut is not None:
		yield dut.copi.eq(dataOut)
		yield dut.copi_oe.eq(1)
	else:
		yield dut.copi_oe.eq(0)
	yield dut.begin.eq(1)
	yield
	yield Settle()
	yield dut.begin.eq(0)
	yield dut.cs.eq(1)
	yield
	yield Settle()
	assert (yield bus.cs.o) == 1
	for i in range(8):
		if dataOut is not None:
			bit = (dataOut >> (7 - i)) & 1
		else:
			bit = 0
		yield
		yield Settle()
		assert (yield bus.clk.o) == 0
		assert (yield bus.copi.o) == bit
		if dataIn is not None:
			bit = (dataIn >> (7 - i)) & 1
			yield bus.cipo.i.eq(bit)
		yield
		yield Settle()
		assert (yield bus.clk.o) == 1
	assert (yield dut.complete) == 1
	yield
	yield Settle()
	assert (yield dut.complete) == 0
	yield dut.cs.eq(0)
	yield
	yield Settle()
	if dataIn is not None:
		assert (yield dut.cipo) == dataIn
	yield

@sim_case(domains = (('sync', 16e6),),
	dut = DUT(resource = bus))
def transactions(sim : Simulator, dut):
	bus = dut._bus
	reset = dut.reset

	def domainSync():
		yield reset.eq(1)
		yield Settle()
		yield
		yield dut.cs.eq(0)
		yield
		yield reset.eq(0)
		yield bus.clk.o.eq(1)
		yield Settle()
		yield
		assert (yield bus.cs.o) == 0
		yield
		yield from performIO(bus = bus, dut = dut, dataOut = 0x5A)
		yield from performIO(bus = bus, dut = dut, dataOut = 0x5A, dataIn = 0xF0)
		yield

	yield domainSync, 'sync'
