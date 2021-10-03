from nmigen import *
from enum import IntEnum, unique
from .bus import Bus

__all__ = (
	'FRAM',
)

@unique
class Opcodes(IntEnum):
	writeEnable = 0b0000_0110
	writeDisable = 0b0000_0100
	readStatusReg = 0b0000_0101
	writeStatusReg = 0b0000_0001
	read = 0b0000_0011
	write = 0b0000_0010

class FRAM(Elaboratable):
	def __init__(self, resourceName : tuple):
		self.address = Signal(11)
		self.dataIn = Signal(8)
		self.dataOut = Signal(8)
		self.read = Signal()
		self.write = Signal()
		self.complete = Signal()

		self._resourceName = resourceName

	def elaborate(self, platform) -> Module:
		m = Module()
		self.fixCOPI(platform.lookup(*self._resourceName))
		m.submodules.bus = bus = Bus(resource = platform.request(*self._resourceName))

		command = Signal(Opcodes)
		m.d.comb += [
			self.complete.eq(0),
		]

		with m.FSM(name = 'fram-fsm'):
			with m.State('IDLE'):
				with m.If(self.read):
					m.d.sync += [
						command.eq(Opcodes.read),
						bus.cs.eq(1),
					]
					m.next = 'ISSUE-CMD'
				with m.Elif(self.write):
					m.next = 'WRITE-ENABLE'
			with m.State('WRITE-ENABLE'):
				m.d.sync += [
					bus.cs.eq(1),
					bus.copi.eq(Opcodes.writeEnable),
				]
				m.d.comb += bus.begin.eq(1)
				m.next = 'WAIT-WRITE'
			with m.State('WAIT-WRITE'):
				with m.If(bus.complete):
					m.d.sync += bus.cs.eq(0)
					m.next = 'WRITE'
			with m.State('WRITE'):
				m.d.sync += [
					command.eq(Opcodes.write),
					bus.cs.eq(1),
				]
				m.next = 'ISSUE-CMD'
			with m.State('ISSUE-CMD'):
				m.d.sync += [
					bus.copi.eq(command),
					bus.copi_oe.eq(1),
				]
				m.d.comb += bus.begin.eq(1)
				m.next = 'ISSUE-ADDR-H'
			with m.State('ISSUE-ADDR-H'):
				with m.If(bus.complete):
					m.d.sync += bus.copi.eq(Cat(self.address[8:11], Const(0, 5)))
					m.d.comb += bus.begin.eq(1)
					m.next = 'ISSUE-ADDR-L'
			with m.State('ISSUE-ADDR-L'):
				with m.If(bus.complete):
					m.d.sync += bus.copi.eq(self.address[0:8])
					m.d.comb += bus.begin.eq(1)
					m.next = 'ISSUE-DATA'
			with m.State('ISSUE-DATA'):
				with m.If(bus.complete):
					with m.If(command == Opcodes.read):
						m.d.sync += bus.copi_oe.eq(0)
					with m.Else():
						m.d.sync += bus.copi.eq(self.dataOut)
					m.d.comb += bus.begin.eq(1)
					m.next = 'ISSUE-DATA-WAIT'
			with m.State('ISSUE-DATA-WAIT'):
				with m.If(bus.complete):
					m.d.sync += [
						bus.cs.eq(0),
						self.dataIn.eq(bus.cipo),
					]
					m.d.comb += self.complete.eq(1)
					m.next = 'IDLE'
		return m

	def fixCOPI(self, resource):
		for io in resource.ios:
			if io.name == 'copi':
				pin = io.ios[0]
				pin.dir = 'oe'
				break
