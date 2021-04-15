import pathlib
from distutils.core import setup

cwd = pathlib.Path(__file__).parent
readme = (cwd / 'README.md').read_text()

setup(
	name = 'beapy',
	packages = ['beapy'],
	version = '0.1',
	license = 'MIT',
	description = (
		'A pandas-based python package for requesting data from the U.S. '
		'Bureau of Economic Analysis'
	),
	long_description = readme,
	long_description_content_type = 'text/markdown',
	author = 'hotzsauce',
	author_email = 'githotz@gmail.com',
	url = 'https://www.github.com/hotzsauce/bea-dev',
	keywords = ['economics', 'bea', 'bureau of economic analysis', 'nipa'],
	install_requires = [
		'numpy',
		'pandas',
		'requests'
	],
	include_package_data = True,
	classifiers = [
		'Developer Status :: 3 - Alpha',
		'License :: OSI Approved :: MIT',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.7'
	]
)
