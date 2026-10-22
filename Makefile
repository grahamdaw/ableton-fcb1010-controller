.PHONY: check test smoke log install

check:
	uv run ruff check
	uv run ruff format --check
	uv run pyright
	uv run pytest

test:
	uv run pytest

smoke:
	uv run python scripts/smoke.py $(if $(PORT),--port "$(PORT)")

log:
	scripts/log.sh

install:
	FCB1010_DEV=1 ./install.sh
