"""
the shape & structure of the economic data from the BEA can vary quite a bit.
this module provides a class for consistent reshaping methods across all the
datasets that the BEA hosts
"""
from __future__ import annotations

import warnings



class DataFormatter(object):

	def __init__(self, data: pd.DataFrame):
		self.data = data

		# get series name, period, and value identifers from columns
		columns = self.data.columns
		self.s_id = columns[0]
		self.p_id = columns[1]
		self.v_id = columns[2]

	def issue_warning(self, add: str = ''):
		msg = (
			"\ncould not reshape data into columns of series with time "
			f"periods in the index. {add}"
		)
		warnings.warn(msg)

	def format(self):

		df = self.data

		# if only one period is requested, make series identifier the index
		#	and the time period the series nmae
		if df[self.p_id].nunique() == 1:
			p = df.loc[:, self.p_id].iloc[0]
			df = df.drop(columns=self.p_id).set_index(self.s_id).squeeze().rename(p)

		else:
			df = self.format_multiperiod()
			df.columns.name = ''

		df.index.name = ''
		return df

	def format_multiperiod(self):

		df = self.data

		try:
			# first attempt is to use pandas built-in pivot function
			fmted = df.pivot(
				index=self.p_id,
				columns=self.s_id,
				values=self.v_id
			)
			return fmted

		except ValueError:

			# the same series may be recorded multiple times in the dataset
			series_period = df[self.s_id].str.cat(df[self.p_id])
			series_period.name = 'sp_id'
			if series_period.nunique() < len(series_period):

				spdf = series_period.to_frame()
				spdf['cum_count'] = spdf.groupby('sp_id').cumcount()

				n_dups = len(series_period) - series_period.nunique()
				if (spdf.cum_count != 0).sum() != n_dups:
					# there is something else going on with the data other than
					#	having duplicate entries
					self.issue_warning('duplicate entries but unusual amounts')
					return df

				# if the only problem is duplicate series, append to the series
				#	name of every duplicate entry after the first the cumcount
				#	minus one
				spdf['dup_label'] = '_' + (spdf.cum_count - 1).astype(str)
				spdf.loc[spdf.cum_count == 0, 'dup_label'] = ''

				df[self.s_id] = df[self.s_id].str.cat(spdf.dup_label)
				fmted = df.pivot(
					index=self.p_id,
					columns=self.s_id,
					values=self.v_id
				)
				return fmted

			else:
				self.issue_warning('unknown error')
				return df
