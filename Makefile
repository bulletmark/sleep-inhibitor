NAME = $(shell basename $(CURDIR))
PYNAME = $(subst -,_,$(NAME))

check:
	ruff check .
	mypy */*.py
	pyright */*.py
	vermin -vv --exclude importlib.resources.files --no-tips -i */*.py */*/*.py
	md-link-checker

build:
	rm -rf dist
	uv build

upload: build
	uv-publish

doc:
	update-readme-usage

clean:
	@rm -vrf *.egg-info */*.egg-info .venv/ build/ dist/ __pycache__/ \
          */__pycache__ */*/__pycache__
