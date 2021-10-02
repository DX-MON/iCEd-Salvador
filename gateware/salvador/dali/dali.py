from nmigen import *
from .types import *
from .serial import Serial
from .decoder import CommandDecoder

__all__ = (
	'DALI',
	'DeviceType',
)

class DALI(Elaboratable):
	def __init__(self, *, interface : Record, deviceType : DeviceType):
		self._interface = interface
		self._deviceType = deviceType
		self.error = Signal()
		self.phyiscalMinLevel = Const(1, 8)

	def elaborate(self, platform):
		m = Module()
		m.submodules.serial = serial = Serial()
		m.submodules.decoder = decoder = CommandDecoder(deviceType = self._deviceType)
		interface = self._interface

		address = Signal(8)
		commandBits = Signal(8)
		command = Signal.like(decoder.command)
		commandData = Signal.like(decoder.data)
		deviceCommand = Signal.like(decoder.deviceCommand)

		actualLevel = Signal(8)
		onLevel = Signal.like(actualLevel)
		failureLevel = Signal.like(actualLevel)
		minLevel = Signal.like(actualLevel)
		maxLevel = Signal.like(actualLevel)
		fadeRate = Signal(range(16))
		fadeTime = Signal(range(16))
		shortAddress = Signal(8)
		searchAddress = Signal(24)
		randomAddress = Signal(24)
		group = Signal(16)
		scene = Array(Signal(8) for _ in range(16))
		status = Signal(8)
		dtr = Signal(8)
		dtr1 = Signal(8)
		dtr2 = Signal(8)
		response = Signal(8)

		m.d.comb += [
			serial.rx.eq(interface.rx.i),
			interface.tx.o.eq(serial.tx),
			self.error.eq(serial.error),

			address.eq(serial.dataOut[8:16]),
			commandBits.eq(serial.dataOut[0:8]),
			decoder.commandByte.eq(commandBits),

			serial.dataIn.eq(response),
		]

		with m.FSM(name = 'dali-fsm'):
			with m.State('RESET'):
				m.next = 'IDLE'
			# Spin until we get a valid command
			with m.State('IDLE'):
				with m.If(serial.dataAvailable):
					m.next = 'DECODE'
			# Decode the command we've been sent
			with m.State('DECODE'):
				m.d.sync += [
					command.eq(decoder.command),
					deviceCommand.eq(decoder.deviceCommand),
					commandData.eq(decoder.data),
				]
				m.next = 'EXECUTE'
			# Disptch the command
			with m.State('EXECUTE'):
				with m.Switch(command):
					with m.Case(DALICommand.lampOff):
						m.d.sync += actualLevel.eq(0)
						m.next = 'IDLE'
					with m.Case(DALICommand.levelToDTR):
						m.d.sync += dtr.eq(actualLevel)
						m.next = 'IDLE'
					with m.Case(DALICommand.queryDTR):
						m.d.sync += response.eq(dtr)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryDeviceType):
						m.d.sync += response.eq(self._deviceType)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'

					with m.Case(DALICommand.queryPhyMinLevel):
						assert self.phyiscalMinLevel.value > 0 and self.phyiscalMinLevel.value < 255
						m.d.sync += response.eq(self.phyiscalMinLevel)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'

					with m.Case(DALICommand.queryDTR1):
						m.d.sync += response.eq(dtr1)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryDTR2):
						m.d.sync += response.eq(dtr2)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryLevel):
						m.d.sync += response.eq(actualLevel)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryMaxLevel):
						m.d.sync += response.eq(maxLevel)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryMinLevel):
						m.d.sync += response.eq(minLevel)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryOnLevel):
						m.d.sync += response.eq(onLevel)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryFailureLevel):
						m.d.sync += response.eq(failureLevel)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryFadeTimeRate):
						m.d.sync += [
							response[0:4].eq(fadeRate),
							response[4:8].eq(fadeTime),
						]
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.querySceneLevel):
						m.d.sync += response.eq(scene[commandData])
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryGroups0_7):
						m.d.sync += response.eq(group[0:8])
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryGroups8_15):
						m.d.sync += response.eq(group[8:16])
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryRandomAddrL):
						m.d.sync += response.eq(randomAddress[0:8])
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryRandomAddrM):
						m.d.sync += response.eq(randomAddress[8:16])
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryRandomAddrH):
						m.d.sync += response.eq(randomAddress[16:24])
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					# If we got a device-type-specific command
					with m.Case(DALICommand.deviceSpecific):
						self._handleDeviceSpecific(m, serial, deviceCommand, response)
					with m.Case(DALICommand.nop):
						m.next = 'IDLE'
					with m.Default():
						m.next = 'IDLE'
			# Resync with the TX completing
			with m.State('WAIT'):
				with m.If(serial.sendComplete):
					m.next = 'IDLE'

		return m

	def _handleDeviceSpecific(self, m, serial, command, response):
		if self._deviceType == DeviceType.led:
			return self._handleLEDCommands(m, serial, command, response)
		raise ValueError(f'DeviceType {self._deviceType} is not supported')

	def _handleLEDCommands(self, m, serial, command, response):
		with m.Switch(command):
			with m.Case(DALILEDCommand.queryExtVersionNumber):
				m.d.sync += response.eq(1)
				m.d.comb += serial.dataSend.eq(1)
				m.next = 'WAIT'
			with m.Case(DALILEDCommand.nop):
				m.next = 'IDLE'
			with m.Default():
				m.next = 'IDLE'
