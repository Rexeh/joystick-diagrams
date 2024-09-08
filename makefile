.DEFAULT_GOAL := build-exe

test: fmt lint unit-test

unit-test:
	@echo "Running unit tests"
	@poetry run pytest -sv --cov-report=term-missing --cov-report html --cov=joystick_diagrams tests/

fmt:
	@echo "Formatting source code"
	@poetry run ruff format ./joystick_diagrams ./tests

lint:
	@echo "Linting source code"
	@poetry run ruff check ./joystick_diagrams ./tests --fix

build-exe: make-version
	@echo "Making Frozen Executable"
	@python setup.py build
	@echo "Creating Installer"
	@cmd /C "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Qp ./installer/config.iss

make-version:
	@echo "Making version manifest"
	@poetry run python joystick_diagrams/version.py

ui:
	@echo "Generating UI python"
	@cmd /C ".\scripts\convert_ui.bat"

pub:
	@poetry publish

pub-test:
	@poetry publish -r test-pypi
