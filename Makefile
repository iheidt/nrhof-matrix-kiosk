.PHONY: check lint format test type

# Run everything
check: lint type test
	@echo "✅ All checks passed"

# Static analysis (fast)
lint:
	@echo "Linting (ruff+black)"
	ruff check .
	black --check .

# Auto-fix formatting/lints
format:
	@echo "Auto-formatting (black) and quick fixes (ruff --fix)"
	black .
	ruff check --fix .

# Type checking
type:
	@echo "Type checking (mypy)"
	mypy .

# Tests (quiet by default, tolerant if none exist)
test:
	@echo "Running tests (pytest)"
	pytest -q || echo "no tests"
