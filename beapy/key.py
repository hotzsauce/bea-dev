"""
saving & updating BEA API key
"""


class BEAKey(object):

	_key_file = 'api_key.txt'
	_key_length = 36

	def __init__(self):
		from pathlib import Path

		bea_dir = Path(__file__).parent
		self.key_file = bea_dir / self._key_file

		if not self.key_file.exists():
			self.key_file.touch()

	def verify_key(self, key):
		"""check length of key"""
		if len(key) != self._key_length:
			raise ValueError("BEA API keys must have {self._key_length} characters")

	def save(self, key):
		"""
		save API key to '/bea/api_key.txt'

		Parameters
		----------
		key : str
			BEA-provided API key
		"""
		if not isinstance(key, str):
			raise TypeError("BEA API key must be a str")

		self.verify_key(key)
		self.key_file.write_text(key)


	def retrieve(self):
		"""
		read & return API key from /bea/api_key.txt

		Returns
		-------
		bea_key : str
		"""
		key = self.key_file.read_text().strip()
		if key:
			self.verify_key(key)
			return key
		else:
			raise ValueError(
				"no saved key to retrieve. use `beapy.save_key` to record "
				"BEA API key"
		)


def save_key(key: str):
	"""
	forward-facing method for saving BEA API key
	"""
	keyring = BEAKey()
	keyring.save(key)


def retrieve_key(*args, **kwargs):
	"""
	retrieving saved BEA API key

	Returns
	-------
	bea_key : str
	"""
	keyring = BEAKey()
	return keyring.retrieve()
