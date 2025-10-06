venv := .venv

test:
	. $(venv)/bin/activate && python -m pytest -q
