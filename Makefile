.PHONY: lint format typecheck test dead docs check
lint:        ; uv run ruff check .
format:      ; uv run ruff format --check .
typecheck:   ; uv run mypy scripts tests
test:        ; uv run pytest
dead:        ; uv run vulture scripts
docs:        ; uv run interrogate -v scripts
check: lint format typecheck test dead docs
