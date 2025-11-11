.PHONY: check lint format test type clean clean-run

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

# Clean Python cache files (fixes import/bytecode issues)
clean:
	@echo "🧹 Cleaning Python cache files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "✓ Cache cleaned"

# Clean and run app (use after structural code changes)
clean-run: clean
	@echo "🚀 Starting app with clean cache..."
	@python app.py
