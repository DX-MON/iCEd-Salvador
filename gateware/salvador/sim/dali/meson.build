project(
	'dali',
	['cpp'],
	default_options: [
		'buildtype=release',
		'cpp_std=c++17',
		'warning_level=3',
		'b_ndebug=if-release',
		'b_lto=true',
		'strip=true'
	],
	license: 'GPL3+',
	version: '0.0.1',
	meson_version: '>= 0.53'
)

cxx = meson.get_compiler('cpp')
yosysConfig = find_program('yosys-config')
yosysInclude = run_command(yosysConfig, '--datdir/include').stdout().strip()

yosys = declare_dependency(
	include_directories: [yosysInclude],
)

executable(
	'readStartup',
	['readStartup.cxx'],
	dependencies: [yosys],
	gnu_symbol_visibility: 'inlineshidden'
)
