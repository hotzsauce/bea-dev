"""

"""
from __future__ import annotations
import json

from pathlib import Path
crosswalkdir = Path(__file__).parent



class Funnel(object):
	"""
	class that ensures the current and deprecated BEA table identifiers are
	mapped to the currently used ones
	"""

	_default_id_fields = tuple()
	_dtype = ''


	def __init__(self, table_name: str, table_dict: dict, json_name: str=''):

		self.table_name = table_name
		self.table_dict = table_dict

		# map all alternative table identifers to the current one
		self._update_mappings()

		self.json_name = json_name


	def _update_mappings(self, *args, **kwargs):
		""" re-create the self._dict attribute that implements the funnelling """

		self._dict = {}
		for k, vdict in self.table_dict.items():
			for _, v in vdict.items():
				self._dict[v] = k


	def add_custom_identifier(self, custom: str, table_name: str):
		"""
		edit the existing json by adding a user-defined table identifer

		Parameters
		----------
		custom : str
			the user's desired custom identifier
		table_name : str
			the BEA's recognized table identifier

		Returns
		-------
		None
		"""

		# we don't want to have two custom identifers of the same name
		already_reffed = self._dict.get(custom, None)
		if already_reffed:
			dtype = self._dtype
			raise KeyError(
				f"custom id '{custom}' is already used to reference {dtype} "
				f"'{already_reffed}'. delete this reference first to redefine "
				"custom id or choose a different identifier"
			)

		extant_ids = self.table_dict[table_name]

		# new fields names are just of the form custom{x}
		field_name = f"custom{len(extant_ids)-len(self._default_id_fields)}"
		extant_ids[field_name] = custom

		self._update_mappings()
		self.write_json()


	def _remove_single_id(self, i: str):
		""" remove a single identifier from json """

		try:
			# `i` is the BEA-recognized table name, so we remove all custom ids
			id_dict = self.table_dict[i]
			self.table_dict[i] = {r: id_dict[r] for r in self._default_id_fields}

		except KeyError:
			# `i` might be a custom id

			try:
				table_id = self._dict[i]
				id_dict = self.table_dict[table_id]

				rm_key = {k for k, v in id_dict.items() if v == i}
				for key in rm_key:
					if key in self._default_id_fields:
						# this really will only happen with 'table_id' field
						raise ValueError(
							f"cannot remove BEA identifier {k}: {id_dict[k]}"
						)
				new_dict = {k: v for k, v in id_dict.items() if k not in rm_key}
				self.table_dict[table_id] = new_dict

			except KeyError:
				raise KeyError(f"unrecognized identifier: '{i}'")


	def remove_custom_identifiers(self, ids: Union[str, Iterable[str]] = ''):
		"""
		remove a single, more than one, or all custom identifers from the existing
		json file

		Parameters
		----------
		ids : str | Iterable[str] ( = '' )
			the custom ids that will be removed.
				- if an empty string, every custom identifier will be removed.
				- if a single custom identifer, only that identifier will be removed
				- if a single valid BEA table identifier, all custom identifiers
					referring to that table will be removed
				- if an iterable of strings, remove custom identifiers according
					to the rules outlined in the prior two bullets

		Returns
		-------
		None
		"""
		if ids:
			if isinstance(ids, str):
				self._remove_single_id(ids)
			else:
				for i in ids:
					self._remove_single_id(i)

		else:
			for k, id_dict in self.table_dict.items():
				self.table_dict[k] = {r: id_dict[r] for r in self._default_id_fields}

		self._update_mappings()
		self.write_json()


	def write_json(self, indent=4, *args, **kwargs):
		""" write json from class' `self._dict` attribute """

		labeled_json = {self.table_name: self.table_dict}
		json_path = crosswalkdir / self.json_name
		with open(json_path, 'w') as json_file:
			json.dump(labeled_json, json_file, indent=indent, **kwargs)


	@classmethod
	def from_json(cls, json_name):
		""" create Funnel object from pre-prepared JSON """

		json_path = crosswalkdir / json_name
		with open(json_path, 'r') as json_file:
			json_dict = json.load(json_file)

			# json's have a single top-level key-value pair, with the key being
			#	the BEA table's name
			key_label = list(json_dict.keys())[0]
			table_dict = json_dict[key_label]

			return Funnel(key_label, table_dict, json_name)


	def __getitem__(self, key):
		try:
			return self._dict[key]
		except KeyError:
			dtype = self._dtype
			raise KeyError(f"no recognized {dtype} with name '{key}'") from None

	def __repr__(self):
		return f"<Funnel[{self.table_name}]>"

	def __contains__(self, key):
		return key in self._dict.keys()



class _Walker(object):

	_stored_jsons = dict()

	def __init__(self, *args, **kwargs):
		self.keys = list(self._stored_jsons.keys())

	def retrieve_funnel(self, key: str):
		"""
		retrieve the Funnel object associated with desired dataset

		Parameters
		----------
		key : str
			the name of the dataset to retrieve. accepted values are the three
			dataset names from BEA that have crosswalks:
				fixed_asst, nipa, underlying

		Returns
		-------
		Funnel
		"""

		try:
			json_obj = self._stored_jsons[key]
			if isinstance(json_obj, str):
				# initialize json funnel & return
				json_funnel = Funnel.from_json(json_obj)

				json_funnel._dtype = self._dtype
				json_funnel._default_id_fields = self._default_id_fields

				self._stored_jsons[key] = json_funnel
				return json_funnel

			# funnel's already initialized, just return
			return json_obj

		except KeyError:
			raise KeyError(f"no stored json corresponding to '{key}'") from None


	def retrieve_funnel_blind(self, table_name: str):
		"""
		retrieve the Funnel that has the requested table

		Parameters
		----------
		table_name : str
			the name of the table of interest

		Returns
		-------
		Funnel
		"""
		for key in self._stored_jsons.keys():
			funnel = self.retrieve_funnel(key)

			if table_name in funnel:
				return funnel

		raise KeyError(f"no NIPA dataset with table name {table_name}")



class _TableWalker(_Walker):

	_stored_jsons = {
		'fixedassets': 'fixedassets.json',
		'nipa': 'nipa.json',
		'niunderlyingdetail': 'niunderlyingdetail.json'
	}
	_dtype = 'table'
	_default_id_fields = ('table_name', 'table_id')


class _DatasetWalker(_Walker):

	_stored_jsons = {
		'datasets': 'datasets.json'
	}
	_dtype = 'dataset'
	_default_id_fields = ('beapy', 'bea')


TableWalker = _TableWalker()
DatasetWalker = _DatasetWalker()


#----------------------------
#	front-facing methods
def ensure_bea_dataset(dataset: str):
	"""
	ensures that the dataset name being used is the BEA's name, not a beapy
	or custom one.

	Parameters
	----------
	dataset: str
		the dataset name

	Returns
	-------
	bea_dataset : str
		the BEA's name for the same dataset
	"""
	funnel = DatasetWalker.retrieve_funnel('datasets')
	return funnel[dataset]


def define_dataset_name(custom: str, dataset_name: str):
	"""
	add a custom identifier to reference BEA datasets

	Parameters
	----------
	custom : str
		the new identifier for a dataset
	dataset_name : str
		the BEA-recognized table name

	Returns
	-------
	None
	"""
	funnel = DatasetWalker.retrieve_funnel('datasets')
	funnel.add_custom_identifier(custom, dataset_name)


def delete_dataset_name(dataset_name: str = ''):
	"""
	remove custom dataset name from crosswalk.

	Parameters
	----------
	dataset_name : str | Iterable[str] ( = '' )
		the dataset name to remove.
			- if an empty string, every custom identifier in datasets.json will
				be removed.
			- if a single custom identifer, only that identifier will be removed.
			- if a single valid BEA dataset identifier, all custom identifiers
				referring to that dataset will be removed.
			- if an iterable of strings, remove custom identifiers according
				to the rules outlined in the prior two bullets

	Returns
	-------
	None
	"""
	funnel = DatasetWalker.retrieve_funnel('datasets')
	funnel.remove_custom_identifiers(dataset_name)


def table_name_by_dataset(dataset: str, key: str):
	"""
	return the currently used BEA table identifier when that table's source
	dataset is known

	Parameters
	----------
	dataset : str
		name of the dataset that holds the desired table
	key : str
		table name or table id

	Returns
	-------
	table_name : str
		name of desired table
	"""
	bea_dataset = ensure_bea_dataset(dataset)
	funnel = TableWalker.retrieve_funnel(bea_dataset)
	return funnel[key]


def fixed_asset_table_name(key: str):
	"""
	return BEA table identifer of table `key` in the fixed asset dataset

	Parameters
	----------
	key : str
		table name or table id

	Returns
	-------
	table_name : str
		name of desired table
	"""
	return table_name_by_dataset('fixedassets', key)


def nipa_table_name(key: str):
	"""
	return BEA table identifer of table `key` in the NIPA dataset

	Parameters
	----------
	key : str
		table name or table id

	Returns
	-------
	table_name : str
		name of desired table
	"""
	return table_name_by_dataset('nipa', key)


def underlying_table_name(key: str):
	"""
	return BEA table identifer of table `key` in the NIPA Underlying dataset

	Parameters
	----------
	key : str
		table name or table id

	Returns
	-------
	table_name : str
		name of desired table
	"""
	return table_name_by_dataset('niunderlyingdetail', key)


def define_table_name(custom: str, table_name: str, dataset: str = ''):
	"""
	allow user to define a custom name for a BEA table.

	Parameters
	----------
	custom : str
		the new identifier for a table
	table_name : str
		the old, BEA-recognized table name
	dataset : str ( = '' )
		the name of the dataset the table resides in

	Returns
	-------
	None
	"""
	if dataset:
		bea_dataset = ensure_bea_dataset(dataset)
		funnel = TableWalker.retrieve_funnel(bea_dataset)
	else:
		funnel = TableWalker.retrieve_funnel_blind(table_name)

	funnel.add_custom_identifier(custom, table_name)


def delete_table_name(
	name: Union[str, Iterable[str]] = '',
	dataset: str = ''
):
	"""
	remove custom name from crosswalk.

	Parameters
	----------
	name : str | Iterable[str]
		the table name to remove.
			- if an empty string, every custom identifier in the dataset will
				be removed. if `dataset` is also not provided, all custom names
				in all datasets are removed. otherwise, only remove custom names
				for datasets provided.
			- if a single custom identifer, only that identifier will be removed.
			- if a single valid BEA table identifier, all custom identifiers
				referring to that table will be removed.
			- if an iterable of strings, remove custom identifiers according
				to the rules outlined in the prior two bullets
	dataset : str
		the dataset that `name` is in

	Returns
	-------
	None
	"""
	if dataset:
		bea_dataset = ensure_bea_dataset(dataset)
		funnel = TableWalker.retrieve_funnel(bea_dataset)
		funnel.remove_custom_identifiers(name)

	else:
		if name:
			funnel = TableWalker.retrieve_funnel_blind(name)
			funnel.remove_custom_identifiers(name)

		else:
			for key in TableWalker.keys:
				funnel = TableWalker.retrieve_funnel(key)
				funnel.remove_custom_identifiers()
