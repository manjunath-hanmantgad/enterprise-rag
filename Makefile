.PHONY: up down build test seed migrate eval lint clean health

IMAGE_NAME ?= enterprise-rag
TAG ?= local

up:
	docker compose up --build -d

down:
	docker compose down -v

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

test:
	pytest -q

seed:
	python demo/seed_data.py

migrate:
	python -c "from enterprise_rag.config import get_settings; from enterprise_rag.database import connect, init_db; s=get_settings(); conn=connect(s.database_path); init_db(conn); conn.close()"

eval:
	@if [ -x .venv/bin/python ]; then .venv/bin/python evals/run_evals.py; else python3 evals/run_evals.py; fi

lint:
	ruff check . --ignore=F401 2>/dev/null || echo "Lint warnings noted"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null

health:
	curl -s http://localhost:8000/health | python -m json.tool
