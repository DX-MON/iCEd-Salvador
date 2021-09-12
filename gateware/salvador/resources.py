from nmigen.build import *

__all__ = ('DALIResource',)

def DALIResource(*args, rx, tx, conn = None, attrs = None):
	ios = [
		Subsignal('rx', Pins(rx, dir = 'i', conn = conn, assert_width = 1)),
		Subsignal('tx', Pins(tx, dir = 'o', conn = conn, assert_width = 1)),
	]
	if attrs is not None:
		ios.append(attrs)
	return Resource.family(*args, default_name = 'dali', ios = ios)
