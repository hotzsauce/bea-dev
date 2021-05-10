"""
module for transforming BEA JSONs and XMLs into BEAResponse objects
"""

from __future__ import annotations

from collections import abc

import warnings

import pandas as pd
import numpy as np

from beapy.formats import DataFormatter



def iterable_not_str(obj):
	return isinstance(obj, abc.Iterable) and not isinstance(obj, str)


def getitem_any_level(dct: dict, key: str, pop: bool = False):
	"""
	the extent to which the BEA's returned objects are inconsistent is surprising.
	i expected some consistencies, but some of them are just stunning. most API
	calls will return a json organized like

		{
			'BEAAPI': {
				'Request': { ... },
				'Result': {
					'Dimensions': { ... },
					'Data': { ... },
					...
				}
			}
		}

	but some of them have 'Data' on the same level as Request and Result, like
	the one generated by the call

		>>> res = bea.data('iip', typeofinvestment='finassetsexclfinderiv',
		>>>		component='chgposprice', frequency='a', year='all')

	is

		{
			'BEAAPI': {
				'Request': { ... },
				'Result': { 'Dimensions': [...] },
				'Data': { ... }
			}
		}

	additional inconsistencies are no comprehensive naming scheme, json dicts
	being stored as strings of dicts, among others.
		this method recursively searches the levels of the nested json dicts for
	the key `key`, and returns. an optional parameter for removing the chosen
	object is available. a KeyError is thrown if it isn't found

	Parameters
	----------
	dct : dict
		a dictionary
	key : str
		the name of the attribute to retrieve
	pop : bool ( = False )
		whether to remove object or not
	"""
	try:
		level_keys = dct.keys()
	except AttributeError:
		if iterable_not_str(dct):
			for d in dct:
				return getitem_any_level(d, key, pop)

		raise KeyError(key) from None

	if key in level_keys:
		if pop:
			return dct.pop(key)
		return dct[key]

	for k in level_keys:
		sub_dict = dct[k]
		try:
			return getitem_any_level(sub_dict, key, pop)
		except KeyError:
			pass

	raise KeyError(f"key {key} was not found at any level of provided dict")



#----------------------------
# API Errors
class BEAAPIError(Exception):

	def __init__(self, err_json: dict):
		err_code = getitem_any_level(err_json, 'APIErrorCode')
		err_desc = getitem_any_level(err_json, 'APIErrorDescription')
		msg = f'API Code: {err_code}. Description: {err_desc}'
		super().__init__(msg)




#----------------------------
# Response Objects
class BEAResponse(object):


	def __init__(
		self,
		request: dict,
		result: dict,
		url: str
	):
		self.request = request
		self.result = result
		self.url = url

	def __repr__(self):
		return f"<{type(self).__class__.__name__}>"


	@classmethod
	def from_response(cls, response: requests.Reponse):
		""" create BEA response from Response object """
		url = response.url
		try:
			bea_json = response.json()

			try:
				err = getitem_any_level(bea_json, 'Error')
				raise BEAAPIError(err) from None

			except KeyError:
				pass


			"""
			request_parameters is of the form
				{
					{'ParameterName': 'p1', 'ParameterValue': 'v1'},
					{'ParameterName': 'p2', 'ParameterValue': 'v2'}, ...
				}
			we transmute into dictionary of form
				{'p1': 'v1', 'p2': 'v2', ...}
			"""
			request_parameters = getitem_any_level(bea_json, 'RequestParam', pop=True)
			request = dict()
			for pdict in request_parameters:
				request[pdict['ParameterName']] = pdict['ParameterValue']

			# result json is too varied to do any prep work like with `request`
			result = getitem_any_level(bea_json, 'Results')

			klass = response_classes[request['METHOD']]
			try:
				return klass(request, result, url, bea_json=bea_json)
			except:
				msg = f"could not create BEAResponse. url is \n{url}"
				raise ValueError(msg)

		except AttributeError:
			raise NotImplementedError(f"cannot create Response without json")



class DatasetListResponse(BEAResponse):

	def __init__(self, request: dict, result: dict, url: str, **kwargs):
		super().__init__(request, result, url)

		self.datasets = dict()
		for d in self.result['Dataset']:
			self.datasets[d['DatasetName']] = d['DatasetDescription']


class ParameterListResponse(BEAResponse):

	def __init__(self, request: dict, result: dict, url: str, **kwargs):
		super().__init__(request, result, url)

		self.parameters = dict()
		for p in self.result['Parameter']:
			name = p.pop('ParameterName')
			self.parameters[name] = p


class ParameterValuesResponse(BEAResponse):

	def __init__(self, request: dict, result: dict, url: str, **kwargs):
		super().__init__(request, result, url)

		self.parameters = dict()
		for p in self.result['ParamValue']:
			key, description = tuple(p.values())
			self.parameters[key] = description


class DataResponse(BEAResponse):

	def __init__(self, request: dict, result: dict, url: str, bea_json: dict):
		super().__init__(request, result, url)
		self.bea_json = bea_json

		# get dimension into dictionary of form
		#	'DimensionName': {'dtype': dtype, 'is_value': bool}
		dimensions = self._safe_access_json_field('Dimensions')
		self.dimensions = dict()
		for dim in dimensions:
			dim_dict = {
				'dtype': dim['DataType'], 'is_value': bool(int(dim['IsValue']))
			}
			self.dimensions[dim['Name']] = dim_dict

		# remove notes from self.bea_json and create dictionary of form
		#	{reference: foot note}
		self.notes = dict()
		try:
			note_list = self._safe_access_json_field('Notes', pop=True)
			for note in note_list:
				self.notes[note['NoteRef']] = note['NoteText']
		except KeyError:
			pass

		# the 'Data' field of the BEA json is a list of dictionaries. the keys
		#	of each dict are the keys of the self.dimensions dictionary
		#	constructed above.
		data_list = self._safe_access_json_field('Data', pop=True)
		df, md = self._construct_data_and_metadata(data_list)
		self.data, self.metadata = df, md


	def _construct_data_and_metadata(self, data: list):
		"""
		initialization method for the data and metadata DataFrames
		"""

		# create dataframe that has both data and metadata
		df_md = pd.DataFrame(data)
		df_md = self._set_unique_index(df_md)

		# UNIT_MULT as in val = DataValue * 10^UNIT_MULT (not always provided)
		data_cols = [self.period_identifier, 'DataValue']
		if 'UNIT_MULT' in self.dimensions:
			data_cols.append('UNIT_MULT')

		meta_cols = [c for c in df_md.columns if c not in data_cols]

		# use .loc so we don't get SettingWithCopyWarning
		df = self._construct_data(df_md.loc[:, data_cols])
		md = self._construct_metadata(df_md.loc[:, meta_cols])
		return df, md


	def _construct_data(self, df: pandas.DataFrame):
		"""
		initialization method for the data DataFrame. cast data values from
		strings to floats, and compute the true value using the exponent in
		the 'UNIT_MULT' field. if there is only one observation period, a
		Series is returned (index is series keys, name is observation period).
		if there is more than one observation period, a DataFrame is returned
		with the index the periods, and column names the series identifieres.

		annual, quarterly, and monthly periods are strings of the form
			annual		: yyyy
			quarterly	: yyyyQq
			monthly		: yyyyMmm
		"""
		# BEA has strings in DataValue fields, with commas too
		df.DataValue = df.DataValue.astype(str).str.replace(',', '')
		try:
			df.DataValue = pd.to_numeric(df.DataValue)
			data_dtype = np.float64

		except ValueError:
			# some entries are not numbers. disclosure reasons; maybe others
			idx = df.DataValue.str.isnumeric()
			df.DataValue[idx] = pd.to_numeric(df.DataValue[idx])
			data_dtype = object

		# compute data from base number & exponent
		try:
			expos = pd.to_numeric(df.UNIT_MULT)
			df['data'] = np.multiply(df.DataValue, np.power(10, expos))
			df = df.drop(columns=['DataValue', 'UNIT_MULT'])

		except AttributeError:
			# no 'UNIT_MULT' column
			df['data'] = df.DataValue
			df = df.drop(columns='DataValue')

		# ensure datatype consistency
		dtypes = dict(zip(df.columns, (str, str, data_dtype)))
		df = df.astype(dtypes)

		p_id = self.period_identifier

		# if only one period is requested, make series identifers the index and
		#	the time period the series name
		if df[p_id].nunique() == 1:
			p = df.loc[:, p_id].iloc[0]
			df = df.drop(columns=p_id).squeeze().rename(p)

		else:
			# otherwise, reshape dataframe from long to wide format, setting dates
			#	as index and series identifiers as columns
			df = df.reset_index()

			formatter = DataFormatter(df)
			df = formatter.format()
			df.columns.name = ''

		df.index.name = ''
		return df


	def _construct_metadata(self, md: pandas.DataFrame):
		"""
		initialization method for metadata DataFrame. replace entries in the
		'NoteRef' column with the footnote text, replacing the 'NoteRef' column
		with a 'Notes' one.
		"""
		# replace footnote references with footnote text
		if self.notes:
			if 'NoteRef' not in md.columns:
				msg = (
					"\nthere are footnotes to this data, but the metadata has no "
					"'NoteRef' column. the footnotes can be accessed in the "
					"`notes` attribute of this DataResponse instance"
				)
				warnings.warn(msg)
			else:
				md['Notes'] = md.NoteRef.map(self.notes)
				md = md.drop(columns='NoteRef')

		# there's a metadata entry for each period, so drop
		return md.drop_duplicates()


	def _set_unique_index(self, df: pandas.DataFrame):
		"""
		initialization method for both data and metadata DataFrames. depending
		on the dataset that houses the underlying data, a different combination
		of metadata fields are used to construct the unique key for each data
		series
		"""
		ids = self.series_identifiers
		if iterable_not_str(ids):
			df['index'] = df[ids.pop(0)]
			for i in ids:
				df['index'] = df['index'].str.cat(df[i], sep='_')
		else:
			df['index'] = df[ids]
		return df.set_index('index', drop=True)


	@property
	def series_identifiers(self):
		"""
		BEA doesn't seem to use a consistent term to identify individual series?

		the index of the data and metadata DataFrames are set using the entries
		in the column names that are returned here
		"""

		dataset = self.request['DATASETNAME'].lower()
		if dataset in ('nipa', 'niunderlyingdetail', 'fixedassets'):
			return 'SeriesCode'
		if dataset in ('gdpbyindustry', 'underlyinggdpbyindustry'):
			return 'Industry'
		if dataset in ('ita', 'iip', 'intlservtrade'):
			return 'TimeSeriesId'
		if dataset == 'mne':
			return ['SeriesID', 'RowCode', 'ColumnCode']
		if dataset == 'inputoutput':
			return ['RowCode', 'ColCode']
		if dataset == 'regional':
			return 'GeoFips'

		raise ValueError(f'no series identifier for {dataset}')


	@property
	def period_identifier(self):
		"""
		BEA doesn't seem to use a consistent term to identify observation periods?
		"""

		dataset = self.request['DATASETNAME'].lower()
		if dataset in (
			'nipa', 'niunderlyingdetail', 'fixedassets',
			'ita', 'iip', 'intlservtrade', 'regional'
		):
			return 'TimePeriod'

		if dataset in (
			'mne', 'underlyinggdpbyindustry', 'gdpbyindustry', 'inputoutput'
		):
			return 'Year'

		raise ValueError(f'no valid period identifier for {dataset}')


	def _safe_access_json_field(self, key, pop=False):
		"""
		sometimes objects that should be dicts are stored as the only element of
		a 1-element list in the BEA API json, or a dict is stored as a string
		representation of a dict. this addresses both of these problems; returning
		a dictionary in either case. if the field is a string or list though, they
		will be returned without modification

		Parameters
		----------
		key : str
			the field name in the `result` block to return
		pop : bool ( = False)
			whether to remove object or not

		Returns
		-------
		result_field : str | dict | list
			value associated with `key`. type depends on `key`
		"""

		field = getitem_any_level(self.bea_json, key, pop)

		if isinstance(field, str):
			# sometimes field result that should be a dict (for example, the
			#	Dimensions field of some UnderlyingGDPByIndustry) requests
			#	a string represeentation of a dictionary
			import ast
			return ast.literal_eval(field)

		return field



response_classes = {
	'GETDATASETLIST': DatasetListResponse,
	'GETPARAMETERLIST': ParameterListResponse,
	'GETPARAMETERVALUES': ParameterValuesResponse,
	'GETPARAMETERVALUESFILTERED': ParameterValuesResponse,
	'GETDATA': DataResponse
}



def create_response(bea_response: request.models.Response):

	return BEAResponse.from_response(bea_response)
