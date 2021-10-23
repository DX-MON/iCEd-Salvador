from typing import Union
from math import ceil
from nmigen import *
from .types import *
from .serial import Serial
from .decoder import CommandDecoder
from ..fram import FRAM

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

		readAddress = Signal(11)

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
		scene = Array(Signal(8, name = f'scene{i}') for i in range(16))
		status = Signal(8)
		dtr = Signal(8)
		dtr1 = Signal(8)
		dtr2 = Signal(8)
		response = Signal(8)
		allowMemoryWrite = Signal()
		powerFailure = Signal(reset = 1)

		m.d.comb += [
			serial.rx.eq(interface.rx.i),
			interface.tx.o.eq(serial.tx),
			self.error.eq(serial.error),

			address.eq(serial.dataOut[8:16]),
			commandBits.eq(serial.dataOut[0:8]),
			decoder.commandByte.eq(commandBits),

			serial.dataIn.eq(response),

			# status[2] indicates whether the lamp is lit
			status[2].eq(actualLevel != 0),
			# status[6] indicates if our short address is ok
			status[6].eq(shortAddress == 255),
			status[7].eq(powerFailure),
		]

		with m.FSM(name = 'dali-fsm'):
			with m.State('STARTUP'):
				m.d.sync += readAddress.eq(0)
				m.next = 'BEGIN-READ'
			with m.State('RESET'):
				m.d.sync += allowMemoryWrite.eq(0)
				m.next = 'IDLE'
			# Spin until we get a valid command
			with m.State('IDLE'):
				with m.If(serial.dataAvailable):
					m.next = 'ADDRESS'
			# Decode the address for what we've just been sent
			with m.State('ADDRESS'):
				# If it's a normal request
				with m.If(~address[7]):
					# And is for our short address
					with m.If(address[1:7] == shortAddress):
						m.next = 'DISPATCH'
					with m.Else():
						m.next = 'IDLE'
				# If we're being group addressed
				with m.Elif(address[5:8] == 0b100):
					# If it's for a group we're in
					with m.If(group.bit_select(address[1:5], 1)):
						m.next = 'DISPATCH'
					with m.Else():
						m.next = 'IDLE'
				# If it's a broadcast command
				with m.Elif(address[1:8] == 0b111_1111):
					m.next = 'DISPATCH'
				# Else if this is a special command
				with m.Else():
					m.next = 'DECODE-SPECIAL'
			# Determine if the request was a power control request or a command
			with m.State('DISPATCH'):
				with m.If(address[0]):
					m.next = 'DECODE'
				with m.Else():
					# Actually needs to be level control logic..
					m.next = 'IDLE'
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
					with m.Case(DALICommand.addToGroup):
						m.d.sync += group.bit_select(commandData, 1).eq(1)
						m.d.sync += persistMemory.address.eq(self.mapRegister(group) + commandData[3]),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.removeFromGroup):
						m.d.sync += group.bit_select(commandData, 1).eq(0)
						m.d.sync += persistMemory.address.eq(self.mapRegister(group) + commandData[3]),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.dtrToShortAddress):
						# TOD: Validate dtr.
						m.d.sync += shortAddress.eq(dtr)
						m.d.sync += persistMemory.address.eq(self.mapRegister(shortAddress)),
						m.next = 'WRITEBACK'
					with m.Case(DALICommand.enableMemoryWrite):
						m.d.sync += allowMemoryWrite.eq(1)
						m.next = 'IDLE'
					with m.Case(DALICommand.queryStatus):
						self.sendRegister(m, response, serial, status)

					with m.Case(DALICommand.queryPowerOn):
						self.sendRegister(m, response, serial, Cat(status[2], Const(0, 7)))

					with m.Case(DALICommand.queryMissingShortAddr):
						self.sendRegister(m, response, serial, Cat(status[6], Const(0, 7)))
					with m.Case(DALICommand.queryVersionNumber):
						# Standard says we answer '1'..
						self.sendRegister(m, response, serial, Const(1, 8))
					with m.Case(DALICommand.queryDTR):
						self.sendRegister(m, response, serial, dtr)
					with m.Case(DALICommand.queryDeviceType):
						self.sendRegister(m, response, serial, self._deviceType)
					with m.Case(DALICommand.queryPhyMinLevel):
						assert self.phyiscalMinLevel.value > 0 and self.phyiscalMinLevel.value < 255
						self.sendRegister(m, response, serial, self.phyiscalMinLevel)
					with m.Case(DALICommand.queryPowerFailure):
						self.sendRegister(m, response, serial, Cat(powerFailure, Const(0, 7)))
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
			# Handle special commands
			with m.State('DECODE-SPECIAL'):
				with m.If(address == 0b1010_0011):
					m.d.sync += dtr.eq(commandBits)
				m.next = 'IDLE'
			# Resync with the TX completing
			with m.State('WAIT'):
				with m.If(serial.sendComplete):
					m.next = 'IDLE'
			# Data writeback state
			with m.State('WRITEBACK'):
				m.d.sync += allowMemoryWrite.eq(0)
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
			# These two states are at the bottom as they make use of the writeback information created above
			with m.State('BEGIN-READ'):
				with m.If(readAddress == self._framNextAddr):
					m.next = 'IDLE'
				with m.Else():
					m.d.sync += persistMemory.address.eq(readAddress)
					m.d.comb += persistMemory.read.eq(1)
					sceneAddress = self.mapRegister(scene)
					groupAddress = self.mapRegister(group)
					with m.If((readAddress >= sceneAddress) & (readAddress < sceneAddress + len(scene))):
						m.d.sync += commandData.eq(readAddress - sceneAddress)
					with m.Elif((readAddress >= groupAddress) & (readAddress < groupAddress + (len(group) // 8))):
						m.d.sync += commandData.eq(readAddress - groupAddress)
					m.next = 'WAIT-READ'
			with m.State('WAIT-READ'):
				with m.If(persistMemory.complete):
					m.next = 'STORE-READ'
			with m.State('STORE-READ'):
					for regName, addr in self._framMap.items():
						if regName == maxLevel.name:
							with m.If(readAddress == addr):
								m.d.sync += maxLevel.eq(persistMemory.dataIn)
						elif regName == minLevel.name:
							with m.Elif(readAddress == addr):
								m.d.sync += minLevel.eq(persistMemory.dataIn)
						elif regName == failureLevel.name:
							with m.Elif(readAddress == addr):
								m.d.sync += failureLevel.eq(persistMemory.dataIn)
						elif regName == onLevel.name:
							with m.Elif(readAddress == addr):
								m.d.sync += onLevel.eq(persistMemory.dataIn)
						elif regName == fadeTime.name:
							with m.Elif(readAddress == addr):
								m.d.sync += fadeTime.eq(persistMemory.dataIn)
						elif regName == fadeRate.name:
							with m.Elif(readAddress == addr):
								m.d.sync += fadeRate.eq(persistMemory.dataIn)
						elif regName == scene._inner[0].name:
							with m.Elif((readAddress >= addr) & (readAddress < addr + len(scene))):
								m.d.sync += scene[commandData].eq(persistMemory.dataIn)
						elif regName == group.name:
							with m.Elif((readAddress >= addr) & (readAddress < addr + (len(group) // 8))):
								m.d.sync += group.bit_select(commandData * 8, 8).eq(persistMemory.dataIn)
						elif regName == shortAddress.name:
							with m.Elif(readAddress == addr):
								m.d.sync += shortAddress.eq(persistMemory.dataIn)
					m.d.sync += readAddress.eq(readAddress + 1)
					m.next = 'BEGIN-READ'

		return m

	def mapRegister(self, register : Union[Signal, Array]):
		if isinstance(register, Signal):
			addr = self._framMap.setdefault(register.name, self._framNextAddr)
			if addr == self._framNextAddr:
				self._framNextAddr += ceil(len(register) / 8)
		else:
			addr = self._framMap.setdefault(register._inner[0].name, self._framNextAddr)
			if addr == self._framNextAddr:
				self._framNextAddr += len(register)
		return addr

	def sendRegister(self, m, response : Signal, serial : Serial, register : Value):
		m.d.sync += [
			response.eq(register),
			#allowMemoryWrite.eq(0),
		]
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
