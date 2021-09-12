from pathlib import Path
from arachne.util import *

from .dali.serial import rxDALI

__all__ = ('runSims',)

resultDir = Path('build')
sims = [
	{
		'name': 'dali.serial',
		'cases': (rxDALI, )
	}
]

def runSims():
	if not resultDir.exists():
		resultDir.mkdir()

	for sim in sims:
		log(f'Running simulation {sim["name"]}...')

		outDir = resultDir / sim['name']
		if not outDir.exists():
			outDir.mkdir()

		for case, name in sim['cases']:
			inf(f' => Running {name}')

			with case.write_vcd(str(outDir / f'{name}.vcd')):
				case.reset()
				case.run()
