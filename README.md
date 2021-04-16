# BEApy

A pandas-based python package for programatically requesting data from the U.S. Bureau of Economic Analysis (BEA).

## Installation

`BEApy` is registered on PyPI, so just use pip to install:
```console
pip install beapy
```
or
```console
python3 -m pip install beapy
```

## Requesting Economic Data

The BEA organizes its data into the following datasets:
- National Income & Product Accounts (NIPA)
- National Income Underlying Detail (NIUnderlyingDetail)
- Multinational Enterprises (MNE)
- Standard Fixed Assets (FixedAssets)
- International Transaction Accounts (ITA)
- International Investment Position (IIP)
- Input-Output Data (InputOutput)
- International Services Trade (IntlServTrade)
- GDP by Industry (GDPByIndustry)
- Regional Economic Data (Regional)
- Underlying GDP by Industry (UnderlyingGDPByIndustry)

The terms in parantheses above are the labels to use when accessing the corresponding dataset using `BEApy`. 

#### Dataset Data

We first initialize an instance of the `beapy.BEA` class, providing it with your personal BEA API key (request a free key [here](https://apps.bea.gov/API/signup/index.cfm)). Then provide the dataset name, table name, and data frequency:

```python
>>> import beapy

>>> bea = beapy.BEA(key=your_personal_api_key)
>>> res = bea.data('nipa', tablename='t10101', frequency='a') # DataResponse
```
This would return a `DataResponse` object that stores the annual data of table 't10101' in its `.data` property, and the associated metadata in `.metadata`, both of which are `pandas` DataFrames. (See below for how to assign more intuitive, human-readable, names to the tables). The `bea.data()` method's keywords necessary to construct a valid API call vary from dataset to dataset; the full list for each one can be retrieved using the`bea.parameter_list(dataset)` method.

This second example retrieves monthly underlying data for 2015 & 2016:
```python
>>> res = bea.data('underlying', tablename='u70205s', frequency='m', year=['2015', '2016'])
>>> res.data

        ALLO03     AUTO35     AUTO40  ...    UPR02    UPR03    UPR05
2015M01  45.83  3726400.0  3542200.0  ...  28471.0  26743.0  24139.0
2015M02  46.03  3619700.0  3481400.0  ...  28797.0  26946.0  24214.0
2015M03  45.77  3924700.0  3740500.0  ...  29038.0  26982.0  24199.0
  ...     ...      ...        ...     ...    ...      ...      ...
2016M10  45.63  3382600.0  3173400.0  ...  29132.0  27052.0  24529.0
2016M11  44.85  3450200.0  3126100.0  ...  28635.0  26812.0  24411.0
2016M12  45.47  3447900.0  3216700.0  ...  28492.0  26897.0  24466.0
[24 rows x 44 columns]
```
Note the index is not formatted as a `pandas` DatetimeIndex, as might be expected. This is because the BEA API can return data of multiple frequencies within the same request, formatting the periods as `yyyy`, `yyyyQq`, and `yyyyMmm` for annual, quarterly, and monthly data, respectively. Casting these to Datetimes would mean, for example, '2000', '2000Q1', and '2000M01' would be indistinguishable. A `pandas` PeriodIndex would not be able to hold the Periods of differing frequencies.


#### Dataset Metadata

Each `DataResponse` object also stores the metadata for the requested table. Using the same response as in the last example, we access the metadata using the `.metadata` attribute:
```python
>>> res.metadata

       TableName SeriesCode  ...  CL_UNIT                        Notes
index                        ...
NSAT     U70205S       NSAT  ...    Level  Table 7.2.5S. Auto and T...
NSAD     U70205S       NSAD  ...    Level  Table 7.2.5S. Auto and T...
NSAF     U70205S       NSAF  ...    Level  Table 7.2.5S. Auto and T...
 ...       ...         ...   ...     ...              ...
UPR03    U70205S      UPR03  ...    Level  Table 7.2.5S. Auto and T...
UPR05    U70205S      UPR05  ...    Level  Table 7.2.5S. Auto and T...
CPA43    U70205S      CPA43  ...    Level  Table 7.2.5S. Auto and T...
```
The information stored in this DataFrame varies from dataset to dataset. For this request, the metadata fields are
```python
>>> res.metadata.columns

Index(['TableName', 'SeriesCode', 'LineNumber', 'LineDescription',
       'METRIC_NAME', 'CL_UNIT', 'Notes'],
      dtype='object')
```
A lot of the meta information relates to how the dataset is organized and displayed in the BEA tables. In this example, 'LineNumber'; in other examples, 'RowNumber', 'ColumnNumber', and the like. Other common ones are 'CL_UNIT' (level, percent change, etc.);  'METRIC_NAME' (Fisher Index, ratio, current dollars); and 'Notes', which are the footnotes of the BEA table.


#### Identifying Series

The BEA doesn't seem to have a consistent term to identify series in a dataset table. The NIPA & NIUnderlyingDetail datasets use the term 'SeriesCode' to uniquely label a series in the data and metadata tables, whereas the IIP dataset uses 'TimeSeriesID'. The entries in these fields are used in the `.metadata` index labels, and the `.data` column labels.

The MNE dataset has a 'SeriesID' field, but it doesn't refer to a single variable in a table. Instead, the 'RowCode' & 'ColumnCode' are additionally needed to locate an individual series. In this case, the entries are concatenated together and separated by underscores to form the column/index labels. For example, a series in the MNE dataset with `SeriesID = 5`, `RowCode = 202`, and `ColumnCode = 5400` will be uniquely identified in the metadata index and data columns by withthe label `5_202_5400`.

The fields that are used to label series in a dataset are stored in the `.series_identifiers` property:
```python
>>> res = bea.data('mne', ...)
>>> res.series_identifiers
['SeriesID', 'RowCode', 'ColumnCode']
```


## Requesting Metadata

BEA stores information about the datasets themselves as well, providing four different methods, which return three different subclasses of the `BEAResponse` class. 

#### Dataset List
The first metadata method simply retrieves the dataset names, along with short descriptions. The `.dataset_list()` method of `beapy.BEA` returns a `DatasetListResponse` object, with a dictionary of those names and descriptions:
```python
>>> import beapy

>>> bea = beapy.BEA(key=your_personal_api_key)
>>> res = bea.dataset_list()
>>> for name, descr in res.datasets.items():
>>>     print(name, ': ', desc)

    'NIPA' :  'Standard NIPA tables'
    'NIUnderlyingDetail' :  'Standard NI underlying detail tables'
    'MNE' :  'Multinational Enterprises'
    ...
```

#### Parameter List
The second method returns a `ParameterListResponse` object, with a dictionary of names and summaries of the parameters that can define an API call. Those parameters differ between datasets though, so some care must be taken.
```python
>>> res = bea.parameter_list('regional')
>>> for name, desc in res.parameters.items():
>>>     print(name, ': ', desc)

'GeoFips' :  {'ParameterDataType': 'string', 'ParameterDescription': ...}
'LineCode' :  {'ParameterIsRequiredFlag': '1', 'MultipleAcceptedFlag': '0', ...}
'TableName' :  {'ParameterDescription': 'Regional income or product table', ...}
'Year' :  {'ParameterDataType': 'string', ...}
```

#### Parameter Values
The third method returns the permissible values of a parameter:
```python
>>> res = bea.parameter_values('intlservtrade', parameter='tradedirection')
>>> for k, v in res.parameters.items():
>>>     print(k, ': ', v)

'Balance' :  'Balance'
'Exports' :  'Exports'
'Imports' :  'Imports'
'SupplementalIns' :  'Supplemental detail on insurance transactions'
```

#### Filtered Parameter Values
The final metadata method retrieves the permissible values of a parameter (called the *target parameter*) based on the other provided parameters, which are provided as keyword arguments. For example,
```python
>>> res = bea.filtered_parameter_values('regional', target='linecode', tablename='sainc1')
>>> for k, v in res.parameters.items():
>>>     print(k, ': ', v)

'1' :  '[SAINC1] Personal income'
'2' :  '[SAINC1] Population'
'3' :  '[SAINC1] Per capita personal income'
```

Multiple parameters can be filtered on at the same time; just provide them as additional keyword arguments.
```python
res = bea.filtered_parameter_values('regional', target='year', tablename='cainc5n', geofips='01001')
```
This returns a list of the valid years in the Regional table 'cainc5n' with geographic code '01001'.


## Saving your API Key

The `beapy.BEA` class can be initialized with or without the BEA-provided key (go [here](https://apps.bea.gov/API/signup/index.cfm) to request your free API key). If the code isn't provided upon initialization, it is assumed your key has been saved with the built-in `beapy.save_key()` method.

Before you initialize the `BEA` class for the first time, use this method to record your key:
```python
>>> import beapy

>>> beapy.save_key('YOUR_PERSONAL_API_KEY_FROM_BEA')
>>> bea = beapy.BEA()
```

The stored API key is automatically overwritten by further calls of the `beapy.save_key()` method.


## Custom Table Names

The table names of the 'NIPA', 'NIUnderlyingDetail', and 'FixedAssets' datasets are not particularly informative or nice to look at. The `beapy` module provides methods that can be used to define custom table names that will be stored for future use.

Use `beapy.define_table_name()` to create a custom reference:
```python
>>> res = bea.data('underlying', tablename='auto_output', year='2016') # raises a BEAAPIError
>>> beapy.define_table_name(custom='auto_output', table_name='u70205s', dataset='underlying')
>>> res = bea.data('underlying', tablename='auto_output', year='2016') # no Error; data in table 'u70205s' is returned
```

A similar method is provided to define other names for the datasets
```python
beapy.define_dataset_name(custom: str, dataset_name: str)
```
