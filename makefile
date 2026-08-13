.DEFAULT_GOAL := build-exe

# Frozen output lands in a fixed location so the Inno script and the Linux
# packaging don't have to guess at cx_Freeze's platform/python specific dir name.
BUILD_DIR := build/app

# Read once, from the manifest make-version generates. Recursive '=' so it is
# only evaluated by the targets that actually reference it.
VERSION = $(shell uv run python -c "import json;print(json.load(open('version_manifest.json'))['version'])")

# ISCC is resolved by packaging/windows/build_installer.bat, which honours an
# ISCC environment variable if you need to point at a non default install.
# Exported so 'make build-installer ISCC=<path>' reaches the batch file too.
export ISCC

test: fmt lint unit-test

unit-test:
	@echo "Running unit tests"
	@uv run pytest -sv --cov-report=term-missing --cov-report html --cov=joystick_diagrams tests/

fmt:
	@echo "Formatting source code"
	@uv run ruff format ./joystick_diagrams ./tests

lint:
	@echo "Linting source code"
	@uv run ruff check ./joystick_diagrams ./tests --fix

# Cross platform: freeze the app into $(BUILD_DIR)
build-app: make-version
	@echo "Making Frozen Executable"
	@uv run python setup.py build_exe --build-exe $(BUILD_DIR)

# Windows: freeze, then wrap in the Inno Setup installer (installer/Output/*.exe)
# The batch wrapper locates ISCC and keeps cmd quoting out of the makefile.
build-installer: build-app
	@echo "Creating Installer"
	@packaging\windows\build_installer.bat $(VERSION)

# Linux: freeze, then stage the launcher alongside it and tar it up
build-tarball: build-app
	@echo "Creating Linux tarball"
	@set -e; \
	VERSION=$$(uv run python -c "import json;print(json.load(open('version_manifest.json'))['version'])"); \
	PKG="joystick-diagrams-$$VERSION"; \
	rm -rf "dist/$$PKG"; \
	mkdir -p dist; \
	cp -r $(BUILD_DIR) "dist/$$PKG"; \
	cp packaging/linux/run.sh packaging/linux/install-desktop.sh packaging/linux/joystick-diagrams.desktop.in "dist/$$PKG/"; \
	chmod +x "dist/$$PKG/run.sh" "dist/$$PKG/install-desktop.sh"; \
	rm -f "dist/$$PKG-linux-x86_64.tar.gz"; \
	tar -czf "dist/$$PKG-linux-x86_64.tar.gz" -C dist "$$PKG"; \
	echo "Wrote dist/$$PKG-linux-x86_64.tar.gz"

# Kept as the historic Windows entry point
build-exe: build-installer

make-version:
	@echo "Making version manifest"
	@uv run python joystick_diagrams/version.py

ui:
	@echo "Generating UI python"
	@cmd /C ".\scripts\convert_ui.bat"

pub:
	@uv publish

pub-test:
	@uv publish --index test-pypi

.PHONY: test unit-test fmt lint build-app build-installer build-tarball build-exe make-version ui pub pub-test
