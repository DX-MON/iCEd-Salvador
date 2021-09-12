from nmigen.build import Resource, Pins, Attrs, Clock
from nmigen.vendor.lattice_ice40 import *
from .resources import *

__all__ = ('SalvadorPlatform',)

class SalvadorPlatform(LatticeICE40Platform):
	device = 'iCE40UP5K'
	package = 'SG48'
	default_clk = 'clk16MHz'

	resources = [
		Resource('clk16MHz', 0, Pins('35', dir='i'), Clock(16e6),
			Attrs(GLOBAL=True, IO_STANDARD='SB_LVCMOS')
		),

		DALIResource(0,
			rx = '9', tx = '10',
			attrs = Attrs(IO_STANDARD='SB_LVCMOS')
		)
	]

	connectors = []
