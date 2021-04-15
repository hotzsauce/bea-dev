"""
request objects corresponding to the four different API methods BEA offers:
	- GetDatasetList
	- GetParameterList
	- GetParameterValues
	- GetParameterValuesFiltered
	- GetData
"""

from beapy.crosswalk.walker import (
	ensure_bea_dataset,
	table_name_by_dataset
)

class BEARequest(object):

	# required and optional keyword parameters for API requests
	required = {'method'}
	optional = {'resultformat'}

	# BEA recognized method name
	method = ''

	def __init__(self, obj):
		self.obj = obj

	def __call__(self, *args, **kwargs):
		klass = type(self).__name__
		raise NotImplementedError(f"no `__call__` method for {klass} objects")

	def __repr__(self):
		return f"<{type(self).__name__}>"

	def bea_dataset(self, dataset):
		""" makes sure the BEA's dataset name is used """
		return ensure_bea_dataset(dataset)


class DatasetListRequest(BEARequest):
	"""
	beapy.BEA.dataset_list(*args, **kwargs)

	retrieve a list of the dataset names

	Returns
	-------
	DatasetListResponse object
	"""
	method = 'getdatasetlist'

	def __call__(self, *args, **kwargs):
		params = {
			'method': self.method,
			'resultformat': self.obj.bea_format
		}
		return self.obj.submit_request(**params)


class ParameterListRequest(BEARequest):
	"""
	beapy.BEA.parameter_list(dataset: str, *args, **kwargs)

	retrieve a list of the parameters (required & optional) for a
	particular dataset

	Parameters
	----------
	dataset : str
		the name of the dataset

	Returns
	-------
	ParameterListResponse object
	"""
	required = {'method', 'datasetname'}
	method = 'getparameterlist'

	def __call__(self, dataset, *args, **kwargs):
		params = {
			'method': self.method,
			'datasetname': self.bea_dataset(dataset),
			'resultformat': self.obj.bea_format
		}
		return self.obj.submit_request(**params)


class ParameterValuesRequest(BEARequest):
	"""
	beapy.BEA.parameter_values(dataset: str, parameter: str, *args, **kwargs)

	retrieve a list of the valid values for a particular parameter

	Parameters
	----------
	dataset : str
		the name of the dataset that holds the parameter
	parameter : str
		the name of the parameter

	Returns
	-------
	ParameterValuesResponse object
	"""
	required = {'method', 'datasetname', 'parametername'}
	method = 'getparametervalues'

	def __call__(self, dataset: str, parameter: str, *args, **kwargs):
		params = {
			'method': self.method,
			'datasetname': self.bea_dataset(dataset),
			'parametername': parameter,
			'resultformat': self.obj.bea_format
		}
		return self.obj.submit_request(**params)



class ParameterValuesFilteredRequest(BEARequest):
	"""
	beapy.BEA.filtered_parameter_values(dataset: str, target: str, *args, **kwargs)

	retrieves a list of the valid values for a particular parameter based on
	other provided parameters. those 'other parameters' should be passed via
	keywords; as in `parameter_name=parameter_value`

	Parameters
	----------
	dataset : str
		the name of the dataset that holds the target parameter
	target : str
		the name of the parameter whose values will be returned

	Returns
	-------
	ParameterValuesResponse
	"""
	required = {'method', 'datasetname', 'targetparameter'}
	method = 'getparametervaluesfiltered'

	def __call__(self, dataset: str, target: str, *args, **kwargs):
		if not kwargs:
			raise ValueError(f"no parameters to filter on. provide them via kwargs")

		params = {
			'method': self.method,
			'datasetname': self.bea_dataset(dataset),
			'targetparameter': target,
			'resultformat': self.obj.bea_format
		}
		for k, v in kwargs.items():
			params[k] = v

		return self.obj.submit_request(**params)



class DataRequest(BEARequest):

	method = 'getdata'

	def __call__(self, dataset: str, **kwargs):

		bea_dataset = self.bea_dataset(dataset)

		params = {
			'method': self.method,
			'datasetname': bea_dataset,
			'resultformat': self.obj.bea_format
		}

		# add other provided kwargs to the params that will be passed to request
		for k, v in kwargs.items():
			params[k] = v

		# some requests don't need table names. if they do, check if its a 
		#	user-defined name of the table
		table_name = kwargs.pop('tablename', None)
		if table_name:
			try:
				bea_table_name = table_name_by_dataset(bea_dataset, table_name)
				params['tablename'] = bea_table_name

			except KeyError:
				# don't have a Funnel object for that dataset
				params['tablename'] = table_name

		return self.obj.submit_request(**params)
