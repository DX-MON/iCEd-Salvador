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

		level = Signal(8)
		dtr = Signal(8)
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
						m.d.sync += level.eq(0)
						m.next = 'IDLE'
					with m.Case(DALICommand.levelToDTR):
						m.d.sync += dtr.eq(level)
						m.next = 'IDLE'
					with m.Case(DALICommand.queryDTR):
						m.d.sync += response.eq(dtr)
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryDeviceType):
						m.d.sync += response.eq(self._deviceType)
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
