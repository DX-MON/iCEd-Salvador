from .platform import SalvadorPlatform
from .salvador import Salvador

def cli():
	from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
	from arachne.cli import register_cli

	parser = ArgumentParser(formatter_class = ArgumentDefaultsHelpFormatter,
		description = 'OPLSniffer')
	actions = parser.add_subparsers(dest = 'action', required = True)
	actions.add_parser('build', help = 'build a bitstream from the design')
	actions.add_parser('prep-sim', help = 'prepare cxxrtl for the C++ based sims')

	register_cli(parser = parser)
	args = parser.parse_args()

	if args.action == 'arachne-sim':
		from arachne.core.sim import run_sims
		run_sims(pkg = 'salvador/sim', result_dir = 'build')
		return 0
	elif args.action == 'prep-sim':
		from nmigen.back.cxxrtl import convert
		from .sim.dali.dali import DALI, interface, DeviceType, Platform
		dut = DALI(interface = interface, deviceType = DeviceType.led, persistResource = ('fram', 0))
		with open('salvador/sim/dali/dali.hxx', 'wb') as file:
			file.write(convert(dut, platform = Platform(clk_freq = 1e6)).encode())
		return 0

	platform = SalvadorPlatform()
	salvador = Salvador()
	if args.action == 'build':
		platform.build(salvador, name = 'iCEdSalvador')
	return 0
