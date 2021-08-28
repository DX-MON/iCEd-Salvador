from nmigen.build import Resource, Pins, Attrs, Clock
from nmigen.vendor.lattice_ice40 import *

class SalvadorPlatform(LatticeICE40Platform):
	device = 'iCE40UP5K'
	package = 'SG48'
