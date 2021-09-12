from .platform import SalvadorPlatform
from .salvador import Salvador

def cli():
	from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
	from arachne.cli import register_cli

	parser = ArgumentParser(formatter_class = ArgumentDefaultsHelpFormatter,
		description = 'OPLSniffer')
	actions = parser.add_subparsers(dest = 'action', required = True)
	actions.add_parser('build', help = 'build a bitstream from the design')

	register_cli(parser = parser)
	args = parser.parse_args()

	if args.action == 'arachne-sim':
		from .sim import runSims
		runSims()
		exit(0)

	platform = SalvadorPlatform()
	salvador = Salvador()
	if args.action == 'build':
		platform.build(salvador, name = 'iCEdSalvador')
