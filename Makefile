.PHONY: adr

adr:
	@if [ -z "$(name)" ]; then echo "Error: name is required. Usage: make adr name=xxx"; exit 1; fi
	@number=$$(ls docs/adr/ | grep -E '^[0-9]{3}-' | wc -l | awk '{printf "%03d", $$1}'); \
	filename="docs/adr/$${number}-$(name).md"; \
	cp docs/adr/000-template.md $$filename; \
	sed -i.bak "s/ADR-XXX: \[タイトル\]/ADR-$${number}: $(name)/g" $$filename; \
	rm -f $$filename.bak; \
	echo "Created $$filename"

dev-db:
	docker compose up -d db

test-db:
	docker compose up -d db_test

dev-server:
	cd server && uv run fastapi dev main.py

dev-client:
	cd client && npm run dev
