#include <exception>
#include <string>
#include <substrate/fd>
#include <substrate/index_sequence>
#include <backends/cxxrtl/cxxrtl_vcd.h>
#include "dali.hxx"

using namespace std::literals::string_literals;
using namespace substrate;

using vcdWriter_t = cxxrtl::vcd_writer;

struct cxxrtlAssertion_t : std::exception
	{ const char *what() const noexcept final { return "state assertion failure"; } };

template<typename T, typename V> void cxxrtlAssert(const T &signal, const V value)
{
	const auto result = signal.template get<V>();
	if (result != value)
		throw cxxrtlAssertion_t{};
}

constexpr inline size_t operator ""_MHz(unsigned long long value) noexcept
	{ return value * 1000 * 1000; }

constexpr static auto clkFrequency{1_MHz};
constexpr static auto bitRate{2400U};

int main(int, char **)
{
	cxxrtl_design::p_top dut{};
	vcdWriter_t vcd{};
	fd_t fd{"readStartup.vcd"s, O_CREAT | O_NOCTTY | O_TRUNC | O_WRONLY, normalMode};
	uint64_t timestamp{};

	const auto writeVCD{
		[&]()
		{
			fd.write(vcd.buffer);
			vcd.buffer.clear();
		}
	};

	const auto cycleClock{
		[&]()
		{
			dut.p_clk.set(false);
			dut.step();
			vcd.sample(timestamp);
			timestamp += 500;
			dut.p_clk.set(true);
			dut.step();
			vcd.sample(timestamp);
			timestamp += 500;
			writeVCD();
		}
	};

	vcd.timescale(1, "ns");
	[&]()
	{
		cxxrtl::debug_items allSignals{};
		dut.debug_info(allSignals, "top "s);
		vcd.add(allSignals);
	}();

	auto &daliRX{dut.p_dali__0____rx____i};
	auto &daliTX{dut.p_dali__0____tx____o};

	auto &framCS{dut.p_persistMemory_2e_bus_2e_fram__spi____cs____o};
	auto &framClk{dut.p_persistMemory_2e_bus_2e_fram__spi____clk____o};
	auto &framCOPI{dut.p_persistMemory_2e_bus_2e_fram__spi____copi____o};
	auto &framCIPO{dut.p_fram__spi____cipo____i};

	const auto waitBitTime{
		[&]()
		{
			for ([[maybe_unused]] const auto _ : indexSequence_t{clkFrequency / bitRate})
				cycleClock();
		}
	};

	const auto sendCommand{
		[&](const uint16_t command)
		{
			// Generate start bit
			daliRX.set(false);
			waitBitTime();
			daliRX.set(true);
			waitBitTime();
			// Send command bits
			for (const auto i : indexSequence_t{16})
			{
				const auto bit{(command >> (15U - i)) & 1U};
				daliRX.set(bit);
				waitBitTime();
				daliRX.set(bit ^ 1U);
				waitBitTime();
			}
			// Stop bits
			daliRX.set(true);
			waitBitTime();
			waitBitTime();
			waitBitTime();
			waitBitTime();
		}
	};

	const auto recvResponse{
		[&]() -> uint8_t
		{
			// Wait for processing
			cycleClock();
			cycleClock();
			cycleClock();
			// Check the DUT generates the correct start bit
			cxxrtlAssert(daliTX, false);
			waitBitTime();
			cxxrtlAssert(daliTX, true);
			waitBitTime();
			uint32_t result{};
			for ([[maybe_unused]] const auto _ : indexSequence_t{8})
			{
				const auto bit{daliTX.get<uint32_t>()};
				result <<= 1U;
				result |= bit;
				waitBitTime();
				cxxrtlAssert(daliTX, bit ^ 1U);
				waitBitTime();
			}
			// Stop bits
			cxxrtlAssert(daliTX, true);
			waitBitTime();
			waitBitTime();
			waitBitTime();
			waitBitTime();
			return static_cast<uint8_t>(result);
		}
	};

	const auto readSPI{
		[&]() -> uint8_t
		{
			uint32_t result{};
			for ([[maybe_unused]] const auto _ : indexSequence_t{8})
			{
				cycleClock();
				cxxrtlAssert(framClk, false);
				cycleClock();
				cxxrtlAssert(framClk, true);
				result <<= 1U;
				result |= framCOPI.get<uint32_t>();
			}
			return static_cast<uint8_t>(result);
		}
	};

	const auto writeSPI{
		[&](const uint8_t data)
		{
			for (const auto bit : indexSequence_t{8})
			{
				cycleClock();
				cxxrtlAssert(framClk, false);
				framCIPO.set((data >> (7U - bit)) & 1U);
				cycleClock();
				cxxrtlAssert(framClk, true);
			}
		}
	};

	const auto writeAddress{
		[&](const uint32_t addr)
		{
			cycleClock();
			cxxrtlAssert(framCS, true);
			cycleClock();
			cycleClock();
			if (readSPI() != 3U)
				throw cxxrtlAssertion_t{};
			cycleClock();
			cycleClock();
			if (readSPI() != uint8_t(addr >> 8U))
				throw cxxrtlAssertion_t{};
			cycleClock();
			cycleClock();
			if (readSPI() != uint8_t(addr & 0xFFU))
				throw cxxrtlAssertion_t{};
			cycleClock();
			cycleClock();
			writeSPI(addr + 5U);
			cycleClock();
			cxxrtlAssert(framCS, false);
			cycleClock();
		}
	};

	dut.p_clk.set(true);
	dut.p_rst.set(true);
	dut.step();
	cycleClock();
	dut.p_rst.set(false);
	daliRX.set(true);
	cycleClock();
	for (const auto i : indexSequence_t{25})
		writeAddress(i);
	waitBitTime();
	// Broadcast "Query Max Level"
	sendCommand(0b1111'1111'1010'0001U);
	// Check the device answered with 5
	if (recvResponse() != 5)
		throw cxxrtlAssertion_t{};
	// Broadcast "Query Min Level"
	sendCommand(0b1111'1111'1010'0010U);
	// Check the device answered with 6
	if (recvResponse() != 6)
		throw cxxrtlAssertion_t{};
	// Broadcast "Query On Level"
	sendCommand(0b1111'1111'1010'0011U);
	// Check the device answered with 8
	if (recvResponse() != 8)
		throw cxxrtlAssertion_t{};
	// Broadcast "Query Failure Level"
	sendCommand(0b1111'1111'1010'0100U);
	// Check the device answered with 7
	if (recvResponse() != 7)
		throw cxxrtlAssertion_t{};
	// Broadcast "Query Fade Time/Rate"
	sendCommand(0b1111'1111'1010'0101U);
	// Check the device answered with 0x9A
	if (recvResponse() != 0x9AU)
		throw cxxrtlAssertion_t{};
	for (const auto scene : indexSequence_t{16})
	{
		// Broadcast "Query Scene Level N"
		sendCommand(0b1111'1111'1011'0000U + scene);
		// Check the device answered with B + scene
		if (recvResponse() != 0xBU + scene)
			throw cxxrtlAssertion_t{};
	}
	// Broadcast "Query Group 0_7"
	sendCommand(0b1111'1111'1100'0000U);
	// Check the device answered with 0x1B
	if (recvResponse() != 0x1BU)
		throw cxxrtlAssertion_t{};
	// Broadcast "Query Group 8_15"
	sendCommand(0b1111'1111'1100'0001U);
	// Check the device answered with 0x1C
	if (recvResponse() != 0x1CU)
		throw cxxrtlAssertion_t{};
	// Send "Query Short Address"
	sendCommand(0b1011'1011'0000'0000U);
	// Check the device answered with 0x1D
	if (recvResponse() != 0x1DU)
		throw cxxrtlAssertion_t{};
	waitBitTime();

	writeVCD();
	return 0;
}
