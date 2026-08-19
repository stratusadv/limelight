set windows-shell := ["powershell.exe", "-c"]

PYTHON := if os() == "linux" { ".venv/bin/python" } else { ".venv/Scripts/python.exe" }

default:
	just --list

setup:
	uv venv --python 3.13 .venv
	uv pip install --python {{PYTHON}} -e .[development]

check: lint types test

lint *ARGS:
	{{PYTHON}} -m ruff check limelight tests {{ARGS}}

test *ARGS:
	{{PYTHON}} -m pytest {{ARGS}}

types *ARGS:
	{{PYTHON}} -m ty check limelight tests {{ARGS}}
