.PHONYS: run deps dev

venv:
	virtualenv venv

requirements-dev.txt:
	pip-compile requirements-dev.in > requirements-dev.txt

requirements.txt:
	pip-compile requirements.in > requirements.txt

dev-deps: requirements-dev.txt
	pip install -r requirements-dev.txt

deps: requirements.txt
	pip install -r requirements.txt

dev: venv requirements-dev.txt requirements.txt deps dev-deps

run:
	python3 app/main.py