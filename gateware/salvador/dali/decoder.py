from nmigen import *
from .types import DALICommand

__all__ = ('CommandDecoder',)

class CommandDecoder(Elaboratable):
	def __init__(self):
		self.commandByte = Signal(8)
		self.command = Signal(DALICommand)
		self.data = Signal(4)

	def elaborate(self, platform) -> Module:
		m = Module()
		commandBits = self.commandByte
		command = self.command
		data = self.data
		with m.Switch(commandBits):
			with m.Case('0000 0000'):
				m.d.comb += command.eq(DALICommand.lampOff)
			with m.Case('0000 0001'):
				m.d.comb += command.eq(DALICommand.fadeUp)
			with m.Case('0000 0010'):
				m.d.comb += command.eq(DALICommand.fadeUp)
			with m.Case('0000 0011'):
				m.d.comb += command.eq(DALICommand.stepUp)
			with m.Case('0000 0100'):
				m.d.comb += command.eq(DALICommand.stepDown)
			with m.Case('0000 0101'):
				m.d.comb += command.eq(DALICommand.gotoMax)
			with m.Case('0000 0110'):
				m.d.comb += command.eq(DALICommand.gotoMin)
			with m.Case('0000 0111'):
				m.d.comb += command.eq(DALICommand.stepDownAndOff)
			with m.Case('0000 1000'):
				m.d.comb += command.eq(DALICommand.stepUpAndOn)
			with m.Case('0000 1001'):
				m.d.comb += command.eq(DALICommand.enableDirectCtrl)
			with m.Case('0000 101-'):
				pass
			with m.Case('0000 11--'):
				pass
			with m.Case('0001 ----'):
				m.d.comb += [
					command.eq(DALICommand.gotoScene),
					data.eq(commandBits[0:4]),
				]
			with m.Case('0010 0000'):
				m.d.comb += command.eq(DALICommand.reset)
			with m.Case('0010 0000'):
				m.d.comb += command.eq(DALICommand.levelToDTR)
			with m.Case('0010 001-'):
				pass
			with m.Case('0010 01--'):
				pass
			with m.Case('0010 100-'):
				pass
			with m.Case('0010 1010'):
				m.d.comb += command.eq(DALICommand.dtrToMaxLevel)
			with m.Case('0010 1011'):
				m.d.comb += command.eq(DALICommand.dtrToMinLevel)
			with m.Case('0010 1100'):
				m.d.comb += command.eq(DALICommand.dtrToSysFailLevel)
			with m.Case('0010 1101'):
				m.d.comb += command.eq(DALICommand.dtrToOnLevel)
			with m.Case('0010 1110'):
				m.d.comb += command.eq(DALICommand.dtrToFadeTime)
			with m.Case('0010 1111'):
				m.d.comb += command.eq(DALICommand.dtrToFadeRate)
			with m.Case('0011 ----'):
				pass
			with m.Case('0100 ----'):
				m.d.comb += command.eq(DALICommand.dtrToScene)
			with m.Case('0101 ----'):
				m.d.comb += command.eq(DALICommand.removeFromScene)
			with m.Case('0110 ----'):
				m.d.comb += command.eq(DALICommand.addToGroup)
			with m.Case('0111 ----'):
				m.d.comb += command.eq(DALICommand.removeFromGroup)
			with m.Case('1000 0000'):
				m.d.comb += command.eq(DALICommand.dtrToShortAddress)
			with m.Case('1000 0001'):
				m.d.comb += command.eq(DALICommand.enableMemoryWrite)
			with m.Case('1000 001-'):
				pass
			with m.Case('1000 01--'):
				pass
			with m.Case('1000 1---'):
				pass
			with m.Case('1001 0000'):
				m.d.comb += command.eq(DALICommand.queryStatus)
			with m.Case('1001 0001'):
				m.d.comb += command.eq(DALICommand.queryControlGear)
			with m.Case('1001 0010'):
				m.d.comb += command.eq(DALICommand.queryFailure)
			with m.Case('1001 0011'):
				m.d.comb += command.eq(DALICommand.queryPowerOn)
			with m.Case('1001 0100'):
				m.d.comb += command.eq(DALICommand.queryLimitError)
			with m.Case('1001 0101'):
				m.d.comb += command.eq(DALICommand.queryResetState)
			with m.Case('1001 0110'):
				m.d.comb += command.eq(DALICommand.queryMissingShortAddr)
			with m.Case('1001 0111'):
				m.d.comb += command.eq(DALICommand.queryVersionNumber)
			with m.Case('1001 1000'):
				m.d.comb += command.eq(DALICommand.queryDTR)
			with m.Case('1001 1001'):
				m.d.comb += command.eq(DALICommand.queryDeviceType)
			with m.Case('1001 1010'):
				m.d.comb += command.eq(DALICommand.queryPhyMinLevel)
			with m.Case('1001 1011'):
				m.d.comb += command.eq(DALICommand.queryPowerFailure)
			with m.Case('1001 1100'):
				m.d.comb += command.eq(DALICommand.queryDTR1)
			with m.Case('1001 1101'):
				m.d.comb += command.eq(DALICommand.queryDTR2)
			with m.Case('1001 111-'):
				pass
			with m.Case('1010 0000'):
				m.d.comb += command.eq(DALICommand.queryLevel)
			with m.Case('1010 0001'):
				m.d.comb += command.eq(DALICommand.queryMaxLevel)
			with m.Case('1010 0010'):
				m.d.comb += command.eq(DALICommand.queryMinLevel)
			with m.Case('1010 0011'):
				m.d.comb += command.eq(DALICommand.queryOnLevel)
			with m.Case('1010 0100'):
				m.d.comb += command.eq(DALICommand.queryFailureLevel)
			with m.Case('1010 0101'):
				m.d.comb += command.eq(DALICommand.queryFadeTimeRate)
			with m.Case('1010 011-'):
				pass
			with m.Case('1010 1---'):
				pass
			with m.Case('1011 ----'):
				m.d.comb += command.eq(DALICommand.querySceneLevel)
			with m.Case('1100 0000'):
				m.d.comb += command.eq(DALICommand.queryGroups0_7)
			with m.Case('1100 0001'):
				m.d.comb += command.eq(DALICommand.queryGroups8_15)
			with m.Case('1100 0010'):
				m.d.comb += command.eq(DALICommand.queryRandomAddrH)
			with m.Case('1100 0011'):
				m.d.comb += command.eq(DALICommand.queryRandomAddrM)
			with m.Case('1100 0100'):
				m.d.comb += command.eq(DALICommand.queryRandomAddrL)
			with m.Case('1100 0101'):
				m.d.comb += command.eq(DALICommand.readMemoryLoc)
			with m.Case('1100 011-'):
				pass
			with m.Case('1100 1---'):
				pass
			with m.Case('1101 ----'):
				pass
			with m.Case('111- ----'):
				m.d.comb += [
					command.eq(DALICommand.typeSpecific),
				]
			with m.Case('1111 1111'):
				m.d.comb += command.eq(DALICommand.queryExtVersionNumber)

		return m
