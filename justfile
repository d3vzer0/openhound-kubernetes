set dotenv-load := true

collect +args='kubernetes /tmp/output/raw/ --progress=log':
    @echo "Collecting data"
    uv run src/main.py collect {{args}}

preprocess +args='kubernetes /tmp/output/raw/kubernetes':
    @echo "Preprocessing data"
    uv run openhound preprocess {{args}}

convert +args='kubernetes /tmp/output/raw/kubernetes /tmp/output/graph/kubernetes':
    @echo "Converting data"
    uv run openhound convert {{args}}

sync:
    @echo "Syncing dependencies"
    uv sync --group dev

lint:
    @echo "Checking code style"
    ruff check .

typecheck:
    @echo "Running type checks"
    uv run mypy src
