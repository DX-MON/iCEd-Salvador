from arachne.core.sim import sim_case
from nmigen import Record
from nmigen.build import Resource, Subsignal, Pins
from nmigen.hdl.rec import DIR_FANIN, DIR_FANOUT
from nmigen.sim import *

from ...dali.dali import *
from ...fram.fram import Opcodes as FRAMOpcodes

__all__ = (
	'deviceAndVersion',
	'addressing',
	'setAndQueryLevels',
	'startupRead'
)

fram_spi = Record(
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
	def __init__(self, *, clk_freq):
		self.clk_freq = clk_freq

	@property
	def default_clk_frequency(self):
		return float(self.clk_freq)

	def lookup(self, name, number):
		assert name == 'fram'
		assert number == 0
		return Resource('fram', 0, Subsignal('copi', Pins('0', dir = 'o')))

	def request(self, name, number):
		assert name == 'fram'
		assert number == 0
		return fram_spi

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

def recvResponse(*, interface, clkFreq, bitRate) -> int:
	# Wait for processing
	yield
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

def validateIdle(*, interface, clkFreq, bitRate):
	# Wait for processing
	yield
	yield
	# Check that the dut *does not* generate a start bit
	assert (yield interface.tx.o) == 1
	yield from waitBitTime(clkFreq, bitRate)
	assert (yield interface.tx.o) == 1
	yield from waitBitTime(clkFreq, bitRate)

@sim_case(domains = (('sync', 16e6),),
	dut = DALI(interface = interface, deviceType = DeviceType.led, persistResource = ('fram', 0)),
	platform = Platform(clk_freq = 16e6))
def deviceAndVersion(sim : Simulator, dut : DALI):
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
		# Broadcast "Query Version Number"
		yield from sendCommand(0b1111_1111_1001_0111, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Check the device answered with 1
		assert (yield from recvResponse(interface = interface, clkFreq = 16e6, bitRate = bitRate)) == 1
		yield
		# Broadcast "Query Extended Version Number"
		yield from sendCommand(0b1111_1111_1111_1111, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Check the device answered with 1
		assert (yield from recvResponse(interface = interface, clkFreq = 16e6, bitRate = bitRate)) == 1
		yield
		yield from waitBitTime(16e6, bitRate)
	yield domainSync, 'sync'

@sim_case(domains = (('sync', 16e6),),
	dut = DALI(interface = interface, deviceType = DeviceType.led, persistResource = ('fram', 0)),
	platform = Platform(clk_freq = 16e6))
def setAndQueryLevels(sim : Simulator, dut : DALI):
	bitRate = 2400
	interface = dut._interface

	def domainSync():
		yield interface.rx.i.eq(1)
		yield Settle()
		yield from waitBitTime(16e6, bitRate)
		# Send "Download to DTR" w/ payload of 254
		yield from sendCommand(0b1010_0011_1111_1110, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		yield
		# Broadcast "Store DTR as Max Level"
		yield from sendCommand(0b1111_1111_0010_1010, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		yield
		# Broadcast "Query Max Level"
		yield from sendCommand(0b1111_1111_1010_0001, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Check the device answered with 254
		assert (yield from recvResponse(interface = interface, clkFreq = 16e6, bitRate = bitRate)) == 254
		yield
		# Send "Download to DTR" w/ payload of 6
		yield from sendCommand(0b1010_0011_0000_0110, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		yield
		# Broadcast "Store DTR as Min Level"
		yield from sendCommand(0b1111_1111_0010_1011, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		yield
		# Broadcast "Query Min Level"
		yield from sendCommand(0b1111_1111_1010_0010, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Check the device answered with 6
		assert (yield from recvResponse(interface = interface, clkFreq = 16e6, bitRate = bitRate)) == 6
		yield
		yield from waitBitTime(16e6, bitRate)
	yield domainSync, 'sync'

@sim_case(domains = (('sync', 16e6),),
	dut = DALI(interface = interface, deviceType = DeviceType.led, persistResource = ('fram', 0)),
	platform = Platform(clk_freq = 16e6))
def addressing(sim : Simulator, dut : DALI):
	bitRate = 2400
	interface = dut._interface

	def domainSync():
		yield interface.rx.i.eq(1)
		yield Settle()
		yield from waitBitTime(16e6, bitRate)
		# Send "Query Device Type" to device 10
		yield from sendCommand(0b0001_0101_1001_1001, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		yield
		yield from validateIdle(interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Send "Query Device Type" to group 10
		yield from sendCommand(0b1001_0101_1001_1001, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		yield
		yield from validateIdle(interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Broadcast "Add To Group" for group 10
		yield from sendCommand(0b1111_1111_0110_1010, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		yield
		# Send "Query Device Type" to group 10
		yield from sendCommand(0b1001_0101_1001_1001, interface = interface, clkFreq = 16e6, bitRate = bitRate)
		# Check the device answered with 6 (LED)
		assert (yield from recvResponse(interface = interface, clkFreq = 16e6, bitRate = bitRate)) == 6
		yield
		yield from waitBitTime(16e6, bitRate)
	yield domainSync, 'sync'

@sim_case(domains = (('sync', 1e6),),
	dut = DALI(interface = interface, deviceType = DeviceType.led, persistResource = ('fram', 0)),
	platform = Platform(clk_freq = 1e6))
def startupRead(sim : Simulator, dut : DALI):
	bitRate = 2400
	interface = dut._interface

	def readSPI():
		result = 0
		for i in range(8):
			yield
			yield Settle()
			assert (yield fram_spi.clk.o) == 0
			yield
			yield Settle()
			assert (yield fram_spi.clk.o) == 1
			result <<= 1
			result |= (yield fram_spi.copi.o)
		return result

	def writeSPI(*, data):
		for i in range(8):
			yield
			yield Settle()
			assert (yield fram_spi.clk.o) == 0
			bit = (data >> (7 - i)) & 1
			yield fram_spi.cipo.i.eq(bit)
			yield
			yield Settle()
			assert (yield fram_spi.clk.o) == 1

	def writeAddress(*, addr):
		yield
		yield Settle()
		assert (yield fram_spi.cs.o) == 1
		yield
		yield
		assert (yield from readSPI()) == FRAMOpcodes.read
		yield
		yield
		assert (yield from readSPI()) == (addr >> 8)
		yield
		yield
		assert (yield from readSPI()) == (addr & 0xFF)
		yield
		yield
		yield from writeSPI(data = addr + 5)
		yield
		yield Settle()
		assert (yield fram_spi.cs.o) == 0
		yield

	def domainSync():
		yield interface.rx.i.eq(1)
		yield Settle()
		for i in range(25):
			yield from writeAddress(addr = i)
		yield from waitBitTime(1e6, bitRate)
		# Broadcast "Query Max Level"
		yield from sendCommand(0b1111_1111_1010_0001, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 5
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 5
		# Broadcast "Query Min Level"
		yield from sendCommand(0b1111_1111_1010_0010, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 6
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 6
		# Broadcast "Query On Level"
		yield from sendCommand(0b1111_1111_1010_0011, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 8
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 8
		# Broadcast "Query Failure Level"
		yield from sendCommand(0b1111_1111_1010_0100, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 7
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 7
		# Broadcast "Query Fade Time/Rate"
		yield from sendCommand(0b1111_1111_1010_0101, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 0x9A
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 0x9A
		for scene in range(16):
			# Broadcast "Query Scene Level N"
			yield from sendCommand(0b1111_1111_1011_0000 + scene, interface = interface, clkFreq = 1e6, bitRate = bitRate)
			# Check the device answered with B + scene
			assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 0xB + scene
		# Broadcast "Query Group 0_7"
		yield from sendCommand(0b1111_1111_1100_0000, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 1B
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 0x1B
		# Broadcast "Query Group 8_15"
		yield from sendCommand(0b1111_1111_1100_0001, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 1C
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 0x1C
		# Send "Query Short Address"
		yield from sendCommand(0b1011_1011_0000_0000, interface = interface, clkFreq = 1e6, bitRate = bitRate)
		# Check the device answered with 1D
		assert (yield from recvResponse(interface = interface, clkFreq = 1e6, bitRate = bitRate)) == 0x1D
		yield from waitBitTime(1e6, bitRate)
	yield domainSync, 'sync'
