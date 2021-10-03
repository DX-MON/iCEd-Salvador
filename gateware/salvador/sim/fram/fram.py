from arachne.core.sim import sim_case
from nmigen import Record
from nmigen.build import Resource, Subsignal, Pins
from nmigen.hdl.rec import DIR_FANIN, DIR_FANOUT
from nmigen.sim import *

from ...fram import *

__all__ = (
	'read',
	'write',
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

class Platform:
	@property
	def default_clk_frequency(self):
		return float(16e6)

	def lookup(self, name, number):
		assert name == 'fram'
		assert number == 0
		return Resource('fram', 0, Subsignal('copi', Pins('0', dir = 'o')))

	def request(self, name, number):
		assert name == 'fram'
		assert number == 0
		return bus

@sim_case(domains = (('sync', 16e6),),
	dut = FRAM(resourceName = ('fram', 0)),
	platform = Platform())
def read(sim : Simulator, dut):
	data = 0x9B

	def domainSync():
		yield
		yield dut.address.eq(1000)
		yield dut.read.eq(1)
		yield
		yield dut.read.eq(0)
		for i in range(18):
			yield
		yield Settle()
		for i in range(18):
			yield
		yield Settle()
		for i in range(18):
			yield
		yield Settle()
		for i in range(2):
			yield
		yield Settle()
		for i in range(8):
			bit = (data >> (7 - i)) & 1
			yield bus.cipo.i.eq(bit)
			yield
			yield
		yield Settle()
		assert (yield dut.complete) == 1
		yield
		yield Settle()
		assert (yield dut.dataIn) == data
		yield

	yield domainSync, 'sync'

@sim_case(domains = (('sync', 16e6),),
	dut = FRAM(resourceName = ('fram', 0)),
	platform = Platform())
def write(sim : Simulator, dut):
	def domainSync():
		yield
		yield dut.address.eq(1000)
		yield dut.dataOut.eq(0xB9)
		yield dut.write.eq(1)
		yield
		yield dut.write.eq(0)
		for i in range(18):
			yield
		yield Settle()
		yield
		for i in range(18):
			yield
		yield Settle()
		for i in range(18):
			yield
		yield Settle()
		for i in range(18):
			yield
		yield Settle()
		for i in range(18):
			yield
		yield Settle()
		yield
		yield Settle()
		assert (yield dut.complete) == 1
		yield
		yield Settle()
		yield

	yield domainSync, 'sync'
