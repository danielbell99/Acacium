set shell := ["zsh", "-cu"]

frontend_pid := "runtime/frontend.pid"
backend_pid := "runtime/backend.pid"

bootstrap:
    mkdir -p runtime data/documents
    uv sync --all-groups
    cd frontend && npm install
    uv run pre-commit install --hook-type pre-commit --hook-type pre-push

dev:
    mkdir -p runtime
    just down-all
    (nohup uv run uvicorn acacium.main:app --app-dir backend/src --host 127.0.0.1 --port 8000 > runtime/backend.log 2>&1 < /dev/null & echo $! > {{backend_pid}})
    (cd frontend && nohup npm run dev -- --host 127.0.0.1 > ../runtime/frontend.log 2>&1 < /dev/null & echo $! > ../{{frontend_pid}})
    echo "Prototype: http://localhost:5173"

down-all:
    if [ -f {{backend_pid}} ]; then kill $(cat {{backend_pid}}) 2>/dev/null || true; rm -f {{backend_pid}}; fi
    if [ -f {{frontend_pid}} ]; then kill $(cat {{frontend_pid}}) 2>/dev/null || true; rm -f {{frontend_pid}}; fi

qa:
    make qa
