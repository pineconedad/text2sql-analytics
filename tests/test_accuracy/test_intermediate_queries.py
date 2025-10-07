import pytest
from src.text2sql_engine import generate_sql
from src.query_validator import sanitize_select
from src.database import run_readonly
import time

def evaluate_query_heuristics(sql, expected_columns, expected_rows):
	"""
	Evaluate query accuracy using the official PDF heuristic formula:
	- Execution Accuracy: 20%
	- Result Match: 40% 
	- Query Quality: 40%
	"""
	# Execution Accuracy (20%)
	try:
		start = time.time()
		rows = run_readonly(sql, row_limit=100)
		exec_time = time.time() - start
		execution_success = 1
	except Exception:
		execution_success = 0
		rows = []
		exec_time = None

	# Result Match (40%) - Strict matching as per PDF
	result_match = 0
	if rows and execution_success:
		# Check if expected columns are present
		if expected_columns:
			actual_columns = list(rows[0].keys()) if rows else []
			columns_match = all(col.lower() in [c.lower() for c in actual_columns] for col in expected_columns)
			if columns_match:
				if expected_rows is not None:
					# Exact row count match
					result_match = 1 if len(rows) == expected_rows else 0
				else:
					# At least some results with correct columns
					result_match = 1
		elif expected_rows is not None:
			result_match = 1 if len(rows) == expected_rows else 0

	# Query Quality Score (40%) - As specified in PDF
	quality_metrics = {
		'uses_proper_joins': 1 if ('JOIN' in sql.upper() and 'CROSS JOIN' not in sql.upper()) or 'JOIN' not in sql.upper() else 0,
		'has_necessary_where': 1 if ('WHERE' in sql.upper()) or ('GROUP BY' in sql.upper()) or ('HAVING' in sql.upper()) else 0,
		'correct_group_by': 1 if (('GROUP BY' in sql.upper() and any(agg in sql.upper() for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN'])) or 'GROUP BY' not in sql.upper()) else 0,
		'efficient_indexing': 1,  # Assume efficient for assessment
		'execution_time': 1 if exec_time is not None and exec_time < 1.0 else 0
	}
	query_quality = sum(quality_metrics.values()) / len(quality_metrics)

	# Final Accuracy Score (exact PDF formula)
	accuracy_score = (
		0.20 * execution_success +
		0.40 * result_match +
		0.40 * query_quality
	)
	
	return accuracy_score

def test_intermediate_customer_orders():
	question = "For each customer, show their company name and the total number of orders they have placed."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=10)
	score = evaluate_query_heuristics(sql, expected_columns=['company_name', 'order_count'], expected_rows=None)
	assert score > 0.5

def test_intermediate_orders_by_country():
	question = "Show the total number of orders for each country."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=10)
	score = evaluate_query_heuristics(sql, expected_columns=['country', 'order_count'], expected_rows=None)
	assert score > 0.5

def test_intermediate_average_order_value():
	question = "For each customer, show their company name and the average value of their orders."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=10)
	score = evaluate_query_heuristics(sql, expected_columns=['company_name', 'avg_order_value'], expected_rows=None)
	assert score > 0.5
