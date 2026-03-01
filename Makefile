.PHONY: install install-backend install-frontend dev backend frontend clean

# Install all dependencies
install: install-backend install-frontend

install-backend:
	pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# Run both backend and frontend (backend in background)
dev:
	@echo "Starting backend on :5001 and frontend on :5173..."
	@trap 'kill 0' INT; \
		python server.py & \
		cd frontend && npm run dev

# Run individually
backend:
	python server.py

frontend:
	cd frontend && npm run dev

# Run the CLI pipeline directly (no server)
run:
	@test -n "$(PROMPT)" || (echo "Usage: make run PROMPT=\"your design prompt\" [ROUNDS=3]" && exit 1)
	python main.py "$(PROMPT)" --rounds $(or $(ROUNDS),3)

# Clean generated outputs
clean:
	rm -rf runs/ wandb/
