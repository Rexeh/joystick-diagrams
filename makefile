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
	@poetry run pylint --rcfile pyproject.toml joystick_diagrams/ tests/

build-exe:
	@echo "Making standard portable package"
	@poetry run setup.py build
	@echo "Making MSI Build"
	@poetry run setup.py build bdist_msi

make-version:
	@echo "Making version manifest"
	@poetry run python joystick_diagrams/classes/version/version.py