.PHONY: build

MODULE:=Sublack.py

dev:
	pipenv install --dev --python 3.6

style: isort black

isort:
	pipenv run isort -y

black:
	pipenv run black $(MODULE)

checks:
	pipenv check

flake8:
	pipenv run python setup.py flake8

shell:
	pipenv shell


dists: requirements.txt sdist wheels

sdist:
	pipenv run python setup.py sdist

wheels:
	pipenv run python setup.py bdist_wheel

deploy: build publish

build: dists

publish:
	pipenv run twine upload --repository-url https://upload.pypi.org/legacy/ dist/

update:
	pipenv update -d

githook: checks style
	
push:
	git status
	git push origin --all
	git push origin --tags

doc:
	pipenv run python setup.py build_sphinx

doc-auto:
	pipenv run sphinx-autobuild docs docs/_build
	
clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts


clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -rf .pytest_cache/

# aliases to gracefully handle typos on poor dev's terminal
check: checks
devel: dev
develop: dev
dist: dists
install: install-system
pypi: pypi-publish
styles: style
test: test-unit
unittest: test-unit
wheel: wheels
