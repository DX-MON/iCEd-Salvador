from nmigen import *
from .types import DALICommand, DeviceType, DALILEDCommand

__all__ = ('CommandDecoder',)

class CommandDecoder(Elaboratable):
	def __init__(self, *, deviceType : DeviceType):
		self._typeDecoder = self.fromDeviceType(deviceType)

		self.commandByte = Signal(8)
		self.command = Signal(DALICommand)
		self.deviceCommand = Signal.like(self._typeDecoder.command)
		self.data = Signal(4)

	def fromDeviceType(self, deviceType : DeviceType):
		if deviceType == DeviceType.led:
			return LEDCommandDecoder()
		raise ValueError(f'DeviceType {deviceType} is not supported')

	def elaborate(self, platform) -> Module:
		m = Module()
		typeDecoder = self._typeDecoder
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
			# with m.Case('0000 101-'):
			# with m.Case('0000 11--'):
			with m.Case('0001 ----'):
				m.d.comb += [
					command.eq(DALICommand.gotoScene),
					data.eq(commandBits[0:4]),
				]
			with m.Case('0010 0000'):
				m.d.comb += command.eq(DALICommand.reset)
			with m.Case('0010 0000'):
				m.d.comb += command.eq(DALICommand.levelToDTR)
			# with m.Case('0010 001-'):
			# with m.Case('0010 01--'):
			# with m.Case('0010 100-'):
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
			# with m.Case('0011 ----'):
			with m.Case('0100 ----'):
				m.d.comb += [
					command.eq(DALICommand.dtrToScene),
					data.eq(commandBits[0:4]),
				]
			with m.Case('0101 ----'):
				m.d.comb += [
					command.eq(DALICommand.removeFromScene),
					data.eq(commandBits[0:4]),
				]
			with m.Case('0110 ----'):
				m.d.comb += [
					command.eq(DALICommand.addToGroup),
					data.eq(commandBits[0:4]),
				]
			with m.Case('0111 ----'):
				m.d.comb += [
					command.eq(DALICommand.removeFromGroup),
					data.eq(commandBits[0:4]),
				]
			with m.Case('1000 0000'):
				m.d.comb += command.eq(DALICommand.dtrToShortAddress)
			with m.Case('1000 0001'):
				m.d.comb += command.eq(DALICommand.enableMemoryWrite)
			# with m.Case('1000 001-'):
			# with m.Case('1000 01--'):
			# with m.Case('1000 1---'):
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
			# with m.Case('1001 111-'):
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
			# with m.Case('1010 011-'):
			# with m.Case('1010 1---'):
			with m.Case('1011 ----'):
				m.d.comb += [
					command.eq(DALICommand.querySceneLevel),
					data.eq(commandBits[0:4]),
				]
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
			# with m.Case('1100 011-'):
			# with m.Case('1100 1---'):
			# with m.Case('1101 ----'):
			with m.Case('111- ----'):
				m.d.comb += [
					command.eq(DALICommand.deviceSpecific),
					typeDecoder.commandBits.eq(commandBits[0:6]),
				]
			with m.Default():
				m.d.comb += command.eq(DALICommand.nop)

		m.d.comb += self.deviceCommand.eq(typeDecoder.command)
		m.submodules.typeDecoder = typeDecoder
		return m

class LEDCommandDecoder(Elaboratable):
	def __init__(self):
		self.commandBits = Signal(5)
		self.command = Signal(DALILEDCommand)

	def elaborate(self, platform) -> Module:
		m = Module()
		command = self.command
		with m.Switch(self.commandBits):
			with m.Case('00000'):
				m.d.comb += command.eq(DALILEDCommand.referenceSystemPower)
			with m.Case('00001'):
				m.d.comb += command.eq(DALILEDCommand.enableCurrentProt)
			with m.Case('00010'):
				m.d.comb += command.eq(DALILEDCommand.disableCurrentProt)
			with m.Case('00011'):
				m.d.comb += command.eq(DALILEDCommand.selectCurve)
			with m.Case('00100'):
				m.d.comb += command.eq(DALILEDCommand.dtrToFastFadeTime)
			# with m.Case('00101'):
			# with m.Case('0011-'):
			# with m.Case('010--'):
			# with m.Case('01100'):
			with m.Case('01101'):
				m.d.comb += command.eq(DALILEDCommand.queryGearType)
			with m.Case('01110'):
				m.d.comb += command.eq(DALILEDCommand.queryDimmingCurve)
			with m.Case('01111'):
				m.d.comb += command.eq(DALILEDCommand.queryOperatingModes)
			with m.Case('10000'):
				m.d.comb += command.eq(DALILEDCommand.queryFeatures)
			with m.Case('10001'):
				m.d.comb += command.eq(DALILEDCommand.queryFailStatus)
			with m.Case('10010'):
				m.d.comb += command.eq(DALILEDCommand.queryShortCircuit)
			with m.Case('10011'):
				m.d.comb += command.eq(DALILEDCommand.queryOpenCircuit)
			with m.Case('10100'):
				m.d.comb += command.eq(DALILEDCommand.queryLoadDecrease)
			with m.Case('10101'):
				m.d.comb += command.eq(DALILEDCommand.queryLoadIncrease)
			with m.Case('10110'):
				m.d.comb += command.eq(DALILEDCommand.queryCurrentProtActive)
			with m.Case('10111'):
				m.d.comb += command.eq(DALILEDCommand.queryThermalShutDown)
			with m.Case('11000'):
				m.d.comb += command.eq(DALILEDCommand.queryThermalOverload)
			with m.Case('11001'):
				m.d.comb += command.eq(DALILEDCommand.queryReferenceRunning)
			with m.Case('11010'):
				m.d.comb += command.eq(DALILEDCommand.queryReferenceFailed)
			with m.Case('11011'):
				m.d.comb += command.eq(DALILEDCommand.queryCurrentProtEn)
			with m.Case('11100'):
				m.d.comb += command.eq(DALILEDCommand.queryOperatingMode)
			with m.Case('11101'):
				m.d.comb += command.eq(DALILEDCommand.queryFastFadeTime)
			with m.Case('11110'):
				m.d.comb += command.eq(DALILEDCommand.queryMinFastFadeTime)
			with m.Case('11111'):
				m.d.comb += command.eq(DALILEDCommand.queryExtVersionNumber)
			with m.Default():
				m.d.comb += command.eq(DALILEDCommand.nop)
		return m
