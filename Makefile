.PHONY: test demo compile serve benchmark stress lint check integration browser showcase property evidence live failure-conformance cost-of-safety outcome-fixture

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

demo:
	PYTHONPATH=src python3 -m aecp demo --run-id ordinary
	PYTHONPATH=src python3 -m aecp demo --run-id outage --scenario outage

compile:
	PYTHONPATH=src python3 -m compileall -q src tests

serve:
	PYTHONPATH=src python3 -m aecp serve

benchmark:
	PYTHONPATH=src python3 -m aecp benchmark

stress:
	PYTHONPATH=src python3 -m aecp stress

lint:
	uv run --locked ruff check .

check: compile test lint

property:
	PYTHONPATH=src uv run --locked python -m unittest discover -s tests/property -v

evidence:
	PYTHONPATH=src python3 -m aecp allocation-study --seeds 30
	PYTHONPATH=src python3 -m aecp performance --operations 300

live:
	PYTHONPATH=src python3 scripts/live_validate.py

integration:
	PYTHONPATH=src python3 scripts/integration_smoke.py

isolation:
	PYTHONPATH=src python3 scripts/isolation_validate.py

failure-conformance:
	PYTHONPATH=src python3 scripts/failure_conformance.py benchmark --output var/failure-conformance.json

cost-of-safety:
	PYTHONPATH=src python3 scripts/failure_conformance.py cost-study --output var/cost-of-safety.json

outcome-fixture:
	python3 scripts/validate_outcome_cases.py examples/outcome_study_cases.fixture.json

browser:
	npm run test:browser

showcase:
	@for allocator in market equal priority evcost central; do \
		PYTHONPATH=src python3 -m aecp demo --run-id compare-$$allocator --scenario burst --budget 300 --scheduler $$allocator; \
	done
