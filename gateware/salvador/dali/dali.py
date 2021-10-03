from typing import Union
from nmigen import *
from .types import *
from .serial import Serial
from .decoder import CommandDecoder

__all__ = (
	'DALI',
	'DeviceType',
)

class DALI(Elaboratable):
	def __init__(self, *, interface : Record, deviceType : DeviceType, persistResource : tuple):
		self._interface = interface
		self._deviceType = deviceType
		self.error = Signal()
		self.phyiscalMinLevel = Const(1, 8)
		self._framMap = {}
		self._framNextAddr = 0
		self._persistResource = persistResource

	def elaborate(self, platform):
		m = Module()
		m.submodules.serial = serial = Serial()
		m.submodules.decoder = decoder = CommandDecoder(deviceType = self._deviceType)
		m.submodules.persistMemory = persistMemory = FRAM(resourceName = self._persistResource)
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
					with m.Case(DALICommand.dtrToMaxLevel):
						with m.If(dtr == 0xFF):
							m.d.sync += maxLevel.eq(254)
						with m.Elif(dtr > minLevel):
							m.d.sync += maxLevel.eq(dtr)
						with m.Else():
							m.d.sync += maxLevel.eq(minLevel)
						# TODO: Check and set actualLevel if it's above the new maxLevel
						m.d.sync += persistMemory.address.eq(self.mapRegister(maxLevel)),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.dtrToMinLevel):
						with m.If(dtr < self.phyiscalMinLevel):
							m.d.sync += minLevel.eq(self.phyiscalMinLevel)
						with m.Elif(dtr > maxLevel):
							m.d.sync += minLevel.eq(maxLevel)
						with m.Else():
							m.d.sync += minLevel.eq(dtr)
						# TODO: Check and set actualLevel if it's below the new levelLevel (unless 0)
						m.d.sync += persistMemory.address.eq(self.mapRegister(minLevel)),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.dtrToFailureLevel):
						m.d.sync += failureLevel.eq(dtr)
						m.d.sync += persistMemory.address.eq(self.mapRegister(failureLevel)),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.dtrToOnLevel):
						m.d.sync += onLevel.eq(dtr)
						m.d.sync += persistMemory.address.eq(self.mapRegister(onLevel)),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.dtrToFadeTime):
						with m.If(dtr > 15):
							m.d.sync += fadeTime.eq(15)
						with m.Else():
							m.d.sync += fadeTime.eq(dtr)
						m.d.sync += persistMemory.address.eq(self.mapRegister(fadeTime)),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.dtrToFadeRate):
						with m.If(dtr > 15):
							m.d.sync += fadeRate.eq(15)
						with m.Else():
							m.d.sync += fadeRate.eq(dtr)
						m.d.sync += persistMemory.address.eq(self.mapRegister(fadeRate)),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.dtrToScene):
						m.d.sync += scene[commandData].eq(dtr)
						m.d.sync += persistMemory.address.eq(self.mapRegister(scene) + commandData),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.removeFromScene):
						m.d.sync += scene[commandData].eq(0xFF)
						m.d.sync += persistMemory.address.eq(self.mapRegister(scene) + commandData),
						m.next = 'WRITEBACK'

					with m.Case(DALICommand.queryDTR):
						self.sendRegister(m, response, serial, dtr)
					with m.Case(DALICommand.queryDeviceType):
						self.sendRegister(m, response, serial, self._deviceType)

					with m.Case(DALICommand.queryPhyMinLevel):
						assert self.phyiscalMinLevel.value > 0 and self.phyiscalMinLevel.value < 255
						self.sendRegister(m, response, serial, self.phyiscalMinLevel)

					with m.Case(DALICommand.queryDTR1):
						self.sendRegister(m, response, serial, dtr1)
					with m.Case(DALICommand.queryDTR2):
						self.sendRegister(m, response, serial, dtr2)
					with m.Case(DALICommand.queryLevel):
						self.sendRegister(m, response, serial, actualLevel)
					with m.Case(DALICommand.queryMaxLevel):
						self.sendRegister(m, response, serial, maxLevel)
					with m.Case(DALICommand.queryMinLevel):
						self.sendRegister(m, response, serial, minLevel)
					with m.Case(DALICommand.queryOnLevel):
						self.sendRegister(m, response, serial, onLevel)
					with m.Case(DALICommand.queryFailureLevel):
						self.sendRegister(m, response, serial, failureLevel)
					with m.Case(DALICommand.queryFadeTimeRate):
						m.d.sync += [
							response[0:4].eq(fadeRate),
							response[4:8].eq(fadeTime),
						]
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.querySceneLevel):
						self.sendRegister(m, response, serial, scene[commandData])
					with m.Case(DALICommand.queryGroups0_7):
						self.sendRegister(m, response, serial, group[0:8])
					with m.Case(DALICommand.queryGroups8_15):
						self.sendRegister(m, response, serial, group[8:16])
					with m.Case(DALICommand.queryRandomAddrL):
						self.sendRegister(m, response, serial, randomAddress[0:8])
						m.d.sync += response.eq(randomAddress[0:8])
						m.d.comb += serial.dataSend.eq(1)
						m.next = 'WAIT'
					with m.Case(DALICommand.queryRandomAddrM):
						self.sendRegister(m, response, serial, randomAddress[8:16])
					with m.Case(DALICommand.queryRandomAddrH):
						self.sendRegister(m, response, serial, randomAddress[16:24])
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
			# Data writeback state
			with m.State('WRITEBACK'):
				with m.Switch(command):
					with m.Case(DALICommand.dtrToMaxLevel):
						m.d.sync += persistMemory.dataOut.eq(maxLevel)
					with m.Case(DALICommand.dtrToMinLevel):
						m.d.sync += persistMemory.dataOut.eq(minLevel)
					with m.Default():
						# ERROR..
						m.next = 'IDLE'
				m.d.comb += persistMemory.write.eq(1)
				m.next = 'WRITEBACK-WAIT'
			with m.State('WRITEBACK-WAIT'):
				with m.If(persistMemory.complete):
					m.next = 'IDLE'

		return m

	def mapRegister(self, register : Union[Signal, Array]):
		if isinstance(register, Signal):
			addr = self._framMap.setdefault(register.name, self._framNextAddr)
			if addr == self._framNextAddr:
				self._framNextAddr += 1
		else:
			addr = self._framMap.setdefault(register._inner[0].name, self._framNextAddr)
			if addr == self._framNextAddr:
				self._framNextAddr += len(register)
		return addr

	def sendRegister(self, m, response : Signal, serial : Serial, register : Signal):
		m.d.sync += response.eq(register)
		m.d.comb += serial.dataSend.eq(1)
		m.next = 'WAIT'

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
