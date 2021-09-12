from nmigen import *
from nmigen.build import Resource
from .serial import Serial

class DALI(Elaboratable):
	def __init__(self, *, interface : Resource):
		self._interface = interface

	def elaborate(self, platform):
		m = Module()
		m.submodules.serial = serial = Serial()
		interface = self._interface

		m.d.comb += [
			serial.rx.eq(interface.rx.i),
			interface.tx.o.eq(serial.tx),
		]
		return m
