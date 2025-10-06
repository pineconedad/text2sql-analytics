# src/data_loader.py
import pandas as pd

def load_csv(path: str, **kwargs) -> 'pd.DataFrame':
	"""
	Load a CSV file and return a pandas DataFrame.
	Uses ISO-8859-1 encoding to handle extended characters.
	Args:
		path (str): Path to CSV file.
		**kwargs: Additional pandas read_csv arguments.
	Returns:
		pd.DataFrame: Loaded data.
	"""
	import pandas as pd
	return pd.read_csv(path, encoding='ISO-8859-1', **kwargs)
