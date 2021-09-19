from arachne.core.sim import sim_case
from nmigen import Record
from nmigen.hdl.rec import DIR_FANIN, DIR_FANOUT
from nmigen.sim import *

from ...dali.dali import *

__all__ = (
	'deviceAndVersion',
)

class Platform:
	@property
	def default_clk_frequency(self):
		return float(16e6)

interface = Record(
	layout = (
		('rx', [
			('i', 1, DIR_FANIN),
		]),
		('tx', [
			('o', 1, DIR_FANOUT),
		])
	),
	name = 'dali_0',
)

def waitBitTime(clkFreq, bitRate):
	for _ in range(int(clkFreq) // bitRate):
		yield
	yield Settle()

def sendCommand(command, *, interface, clkFreq, bitRate):
	# Generate state bit
	yield interface.rx.i.eq(0)
	yield from waitBitTime(clkFreq, bitRate)
	yield interface.rx.i.eq(1)
	yield from waitBitTime(clkFreq, bitRate)
	# Send command bits
	for i in range(16):
		bit = (command >> (15 - i)) & 1
		yield interface.rx.i.eq(bit)
		yield from waitBitTime(clkFreq, bitRate)
		yield interface.rx.i.eq(bit ^ 1)
		yield from waitBitTime(clkFreq, bitRate)
	# Stop bits
	yield interface.rx.i.eq(1)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)

def recvResponse(*, interface, clkFreq, bitRate):
	# Wait for processing
	yield
	yield
	# Check the dut generates the correct start bit
	assert (yield interface.tx.o) == 0
	yield from waitBitTime(clkFreq, bitRate)
	assert (yield interface.tx.o) == 1
	yield from waitBitTime(clkFreq, bitRate)
	response = 0
	for i in range(8):
		bit = (yield interface.tx.o)
		response <<= 1
		response |= bit
		yield from waitBitTime(clkFreq, bitRate)
		assert (yield interface.tx.o) == bit ^ 1
		yield from waitBitTime(clkFreq, bitRate)
	# Stop bits
	assert (yield interface.tx.o) == 1
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)
	yield from waitBitTime(clkFreq, bitRate)
	return response

@sim_case(domains = (('sync', 16e6),),
	dut = DALI(interface = interface, deviceType = DeviceType.led),
	platform = Platform())
def deviceAndVersion(sim : Simulator, dut):
	bitRate = 2400
	interface = dut._interface

	def domainSync():
		yield interface.rx.i.eq(1)
		yield Settle()
		yield from waitBitTime(16e6, bitRate)
		# Broadcast "Query Device Type"
		yield from sendCommand(0b1111_1111_1001_1001, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Check the device answered with 6 (LED)
		assert (yield from recvResponse(interface = interface, clkFreq = 16e6, bitRate = bitRate)) == 6
		yield
		# Broadcast "Query Extended Version Number"
		yield from sendCommand(0b1111_1111_1111_1111, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Check the device answered with 1
		assert (yield from recvResponse(interface = interface, clkFreq = 16e6, bitRate = bitRate)) == 1

		yield from waitBitTime(16e6, bitRate)

	yield domainSync, 'sync'
