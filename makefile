.DEFAULT_GOAL := build-exe

test: fmt lint unit-test

unit-test:
	@echo "Running unit tests"
	@poetry run pytest -sv --cov-report term-missing --cov=src tests/
	
fmt:
	@echo "Formatting source code"
	@poetry run black .

lint: 
	@echo "Linting source code"
	@poetry run pylint --rcfile pyproject.toml src/ tests/

build-exe:
	@poetry run python build.py build