.DEFAULT_GOAL := build-exe

test: fmt lint unit-test

unit-test:
	@echo "Running unit tests"
	@poetry run pytest -sv --cov-report html --cov=joystick_diagrams/ tests/
	
fmt:
	@echo "Formatting source code"
	@poetry run black ./joystick_diagrams

lint: 
	@echo "Linting source code"
	@poetry run pylint --rcfile pyproject.toml joystick_diagrams/ tests/

build-exe:
	@echo "Making standard portable package"
	@python setup.py build
	@echo "Making MSI Build"
	@python setup.py build bdist_msi

make-version:
	@echo "Making version manifest"
	@poetry run python joystick_diagrams/classes/version/version.py