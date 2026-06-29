ORCA := node node_modules/@orcalang/orca-lang/dist/index.js

.PHONY: install verify-machines dev test migrate worker

install:
	npm install
	pip install -e ".[dev]"

migrate:
	alembic upgrade head

worker:
	python -m backend.pipeline.worker

# Topology-verify every machine. Non-zero exit fails the target (the CI + boot gate).
verify-machines:
	@set -e; for m in machines/*.orca.md; do \
	  echo "==> verify $$m"; \
	  $(ORCA) verify $$m; \
	done

dev:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -q
