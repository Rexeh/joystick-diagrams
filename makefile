.DEFAULT_GOAL := build-exe

test: lint unit-test fmt

unit-test:
	@echo "Running unit tests"
	@poetry run pytest --cov-report term-missing --cov=src tests/
	
fmt:
	@echo "Formatting source code"
	@poetry run black .

lint: 
	@echo "Linting source code"
	@poetry run pylint --rcfile pyproject.toml src/ tests/

build-exe:
	@python build.py build