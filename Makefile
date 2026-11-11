.PHONY: build check preview test
build:
	python3 scripts/build.py
check: build
	python3 scripts/check.py
	node --check site/site.js
preview: build
	python3 -m http.server 8000 --bind 127.0.0.1 --directory _site
test:
	uv run pytest -q
