from nmigen import *
from nmigen.build import Resource
from .types import DeviceType
from .serial import Serial
from .decoder import CommandDecoder

__all__ = ('DALI',)

class DALI(Elaboratable):
	def __init__(self, *, interface : Resource):
		self._interface = interface

	def elaborate(self, platform):
		m = Module()
		m.submodules.serial = serial = Serial()
		m.submodules.decoder = decoder = CommandDecoder(deviceType = DeviceType.led)
		interface = self._interface

		address = Signal(8)
		command = Signal(8)

		m.d.comb += [
			serial.rx.eq(interface.rx.i),
			interface.tx.o.eq(serial.tx),
			address.eq(serial.dataOut[8:16]),
			command.eq(serial.dataOut[0:8]),
			decoder.commandByte.eq(command),
		]
		return m
