"""

"""
from __future__ import annotations
import requests


from beapy.key import retrieve_key
from beapy.bea_responses import create_response
import beapy.bea_requests as req



class CachedAccessor(object):

	def __init__(self, name: str, accessor) -> None:
		self._name = name
		self._accessor = accessor

	def __get__(self, obj, cls):
		if obj is None:
			return self._accessor

		accessor_obj = self._accessor(obj)
		object.__setattr__(obj, self._name, accessor_obj)
		return accessor_obj



class BEA(object):

	# uniform resource identifer & url for requesting API key
	_uri = 'https://apps.bea.gov/api/data/'
	_register_url = 'https://apps.bea.gov/api/signup/'

	def __init__(
		self,
		key: str = '',
		bea_format: str = 'json'
	):

		if not key:
			try:
				key = retrieve_key()
			except ValueError:
				import os
				key = os.getenv('BEA_API_KEY')

		if not key:
			raise ValueError(
				"BEA API key must provided through the 'key' parameter, saved "
				"with the `beapy.save_key` method, or stored in the environment "
				"variable 'BEA_API_KEY'. New keys can be requested at "
				f"{self._register_url}"
			)

		# save key & update the uniform resource identifer with UserID
		self.key = key
		self._uri = self._uri + f'?&userid={self.key}'

		try:
			self.bea_format = bea_format.lower()
		except AttributeError:
			raise TypeError("'bea_format' paramter must be str")

	def __repr__(self):
		return "<BEAObject>"

	# methods corresponding exactly to BEA's API methods
	dataset_list = CachedAccessor(
		'dataset_list', req.DatasetListRequest)
	parameter_list = CachedAccessor(
		'parameter_list', req.ParameterListRequest)
	parameter_values = CachedAccessor(
		'parameter_values', req.ParameterValuesRequest)
	filtered_parameter_values = CachedAccessor(
		'filtered_parameter_values', req.ParameterValuesFilteredRequest)
	data = CachedAccessor('data', req.DataRequest)


	def submit_request(self, **kwargs):
		response = requests.get(self._uri, kwargs)
		return create_response(response)
