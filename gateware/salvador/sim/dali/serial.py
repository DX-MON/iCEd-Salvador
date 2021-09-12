from arachne.core.sim import sim_case
from nmigen.sim import *

from ...dali.serial import Serial

__all__ = ('rxDALI', )

class Platform:
	@property
	def default_clk_frequency(self):
		return float(16e6)

def waitBitTime(clkFreq, bitRate):
	for _ in range(int(clkFreq) // bitRate):
		yield
	yield Settle()

def sendCommand(command, *, dut, clkFreq, bitRate):
	# Generate state bit
	yield dut.rx.eq(0)
	yield from waitBitTime(clkFreq, bitRate)
	yield dut.rx.eq(1)
	yield from waitBitTime(clkFreq, bitRate)
	# Send command bits
	for i in range(16):
		bit = (command >> (15 - i)) & 1
		yield dut.rx.eq(bit)
		yield from waitBitTime(clkFreq, bitRate)
		yield dut.rx.eq(bit ^ 1)
		yield from waitBitTime(clkFreq, bitRate)
	# Stop bits
	yield dut.rx.eq(1)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)

@sim_case(domains = (('sync', 16e6),), dut = Serial(), platform = Platform())
def rxDALI(sim : Simulator, dut):
	def domainSync():
		yield Settle()
		yield
		yield
		yield dut.rx.eq(1)
		yield
		yield Settle()
		yield from waitBitTime(16e6, dut._bitRate)
		# Broadcast "Query Short Address"
		yield from sendCommand(0b1111_1111_1001_0110, dut = dut, clkFreq = 16e6, bitRate = dut._bitRate)
		yield
		yield

	yield domainSync, 'sync'
