import pytest
from src.text2sql_engine import generate_sql
from src.query_validator import sanitize_select
from src.database import run_readonly
import time

def evaluate_query_heuristics(sql, expected_columns, expected_rows):
	# Execution Accuracy
	try:
		start = time.time()
		rows = run_readonly(sql, row_limit=100)
		exec_time = time.time() - start
		execution_success = 1
	except Exception:
		execution_success = 0
		rows = []
		exec_time = None

	# Result Match
	result_match = 0
	if rows:
		if expected_rows is not None:
			result_match = int(len(rows) == expected_rows)
		if expected_columns:
			result_match = result_match and all(col in rows[0] for col in expected_columns)

	# Query Quality
	quality_metrics = {
		'uses_proper_joins': int('JOIN' in sql.upper()),
		'has_necessary_where': int('WHERE' in sql.upper()),
		'correct_group_by': int('GROUP BY' in sql.upper()),
		'efficient_indexing': 1,  # Assume indexed for demo
		'execution_time': int(exec_time is not None and exec_time < 1)
	}
	query_quality = sum(quality_metrics.values()) / len(quality_metrics)

	# Final Accuracy Score
	accuracy_score = (
		0.20 * execution_success +
		0.40 * result_match +
		0.40 * query_quality
	)
	return accuracy_score

def test_simple_customer_list():
	question = "List all company names of customers."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=10)
	score = evaluate_query_heuristics(sql, expected_columns=['companyName'], expected_rows=None)
	assert score > 0.5

def test_simple_product_names():
	question = "Show the names of all products."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=10)
	score = evaluate_query_heuristics(sql, expected_columns=['productName'], expected_rows=None)
	assert score > 0.5

def test_simple_order_dates():
	question = "List the order dates for all orders."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=10)
	score = evaluate_query_heuristics(sql, expected_columns=['orderDate'], expected_rows=None)
	assert score > 0.5
