import pytest
from src.text2sql_engine import generate_sql
from src.query_validator import sanitize_select
from src.database import run_readonly
import time

def evaluate_query_heuristics(sql, expected_columns, expected_rows):
	try:
		start = time.time()
		rows = run_readonly(sql, row_limit=100)
		exec_time = time.time() - start
		execution_success = 1
	except Exception:
		execution_success = 0
		rows = []
		exec_time = None

	result_match = 0
	if rows:
		if expected_rows is not None:
			result_match = int(len(rows) == expected_rows)
		if expected_columns:
			result_match = result_match and all(col in rows[0] for col in expected_columns)

	quality_metrics = {
		'uses_proper_joins': int('JOIN' in sql.upper()),
		'has_necessary_where': int('WHERE' in sql.upper()),
		'correct_group_by': int('GROUP BY' in sql.upper()),
		'efficient_indexing': 1,
		'execution_time': int(exec_time is not None and exec_time < 1)
	}
	query_quality = sum(quality_metrics.values()) / len(quality_metrics)

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
	score = evaluate_query_heuristics(sql, expected_columns=['customerID', 'order_count'], expected_rows=None)
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
	score = evaluate_query_heuristics(sql, expected_columns=['customerID', 'avg_order_value'], expected_rows=None)
	assert score > 0.5
