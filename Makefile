.PHONY: all
all: test lint type_check

.PHONY: test
test:
	python -m pytest tests/

.PHONY: lint
lint:
	python -m pylint src/ examples/ tests/
	jshint --show-non-errors src/pura/static/js/
	@find src -name '*.html' | xargs -iXX sh -c 'echo tidy XX; sed s/{{.*}}/abc/ < XX | tidy -eq'

.PHONY: type_check
type_check:
	mypy --ignore-missing-imports src/ examples/ tests/

# upgrade all deps:
#   make -W test-requirements.{in,txt} PIP_COMPILE_ARGS="-U"
# upgrade specific deps:
#   make -W test-requirements.{in,txt} PIP_COMPILE_ARGS="-P foo"
test-requirements.txt: setup.py test-requirements.in
	pip-compile -q $(PIP_COMPILE_ARGS) --output-file $@ $^

test-requirements-trio.txt: setup.py test-requirements.in
	pip-compile -q $(PIP_COMPILE_ARGS) --extra trio --output-file $@ $^
