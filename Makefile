.PHONY: all
all: test lint type_check

.PHONY: test
test:
	python -m pytest tests/

.PHONY: lint
lint:
	python -m pylint src/ examples/ tests/
	jshint --show-non-errors src/pura/html/js/
	tidy -eq src/pura/html/*.html

.PHONY: type_check
type_check:
	mypy --ignore-missing-imports src/ examples/ tests/

pinned-requirements.txt: setup.py
	pip-compile --output-file $@

test-requirements.txt: test-requirements.in
	pip-compile --output-file $@ $<
