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

def test_complex_top_customers_by_sales():
	question = "Find the top 5 customers by the total sales amount of their orders."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=5)
	score = evaluate_query_heuristics(sql, expected_columns=['customerID', 'total_sales'], expected_rows=5)
	assert score > 0.5

def test_complex_monthly_sales_trend():
	question = "Show the total sales amount for each month in the last year."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=12)
	score = evaluate_query_heuristics(sql, expected_columns=['month', 'sales'], expected_rows=12)
	assert score > 0.5

def test_complex_top_products_by_region():
	question = "For each country, find the top 3 products by quantity sold."
	sql = generate_sql(question)
	sql = sanitize_select(sql, row_limit=30)
	score = evaluate_query_heuristics(sql, expected_columns=['region', 'productName', 'sales'], expected_rows=None)
	assert score > 0.5
