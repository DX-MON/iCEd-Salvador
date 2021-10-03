from nmigen import *
from .dali import *

class Salvador(Elaboratable):
	def elaborate(self, platform):
		m = Module()
		m.submodules.dali = DALI(interface = platform.request('dali'), deviceType = DeviceType.led,
			persistResource = ('fram', 0))
		return m
