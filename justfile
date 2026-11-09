set shell := ["sh", "-c"]
set windows-shell := ["powershell.exe", "-c"]

python := if os_family() == "windows" { ".venv/Scripts/python.exe" } else { ".venv/bin/python" }

[doc('Build the overlay bundles into the package')]
build:
    node build.ts

[doc('Type-check the examples, the package, the tests, and the overlay')]
check:
    {{ python }} -m ty check examples limelight tests
    npx tsc --project tsconfig.json

[doc('Run the continuous integration pipeline')]
ci:
    uv lock --check
    {{ python }} -m ruff format --check examples limelight scripts tests
    {{ python }} -m ruff check examples limelight scripts tests
    {{ python }} -m ty check examples limelight tests
    npx tsc --project tsconfig.json
    npx eslint --flag unstable_native_nodejs_ts_config --max-warnings 0 .
    node --test "src/**/*.test.ts"
    node build.ts
    git diff --exit-code -- limelight/overlay/assets limelight/scripts
    {{ python }} -m pytest
    just example

[doc('Build the documentation site and fail on a broken link')]
docs:
    uv run --only-group docs zensical build --strict

[doc('Run the examples')]
example:
    {{ python }} examples/lost_click.py
    {{ python }} examples/order_approval.py
    {{ python }} examples/order_metrics.py
    {{ python }} examples/order_search.py
    {{ python }} examples/row_menu.py
    {{ python }} -m pytest --quiet -p limelight.pytest_plugin examples/test_order_approval.py
    {{ python }} examples/voiceover_holds.py

[doc('Apply the ruff and ESLint fixes')]
fix:
    {{ python }} -m ruff check examples limelight scripts tests --fix
    npx eslint --flag unstable_native_nodejs_ts_config --max-warnings 0 --fix .

[doc('Format the examples, the package, the scripts, and the tests')]
fmt:
    {{ python }} -m ruff format examples limelight scripts tests

[doc('Lint the tree with tigerstyle-lsp, the Python with ruff, and the overlay with ESLint, and check the Python format')]
lint:
    tigerstyle-lsp check . --format concise
    {{ python }} -m ruff check examples limelight scripts tests
    npx eslint --flag unstable_native_nodejs_ts_config --max-warnings 0 .
    {{ python }} -m ruff format --check examples limelight scripts tests

[default]
[doc('List every recipe')]
list:
    @just --list

[doc('Serve the documentation site with live reload')]
run-docs:
    uv run --only-group docs zensical serve

[doc('Install the dependencies and the package in development mode')]
setup:
    npm ci
    uv venv --python 3.13 .venv
    uv pip install --python {{ python }} -e .[development]

[doc('Run the Python tests: just test [pytest arguments]')]
test *arguments:
    {{ python }} -m pytest {{ arguments }}

[doc('Run the overlay tests: just test-ts [node test arguments]')]
test-ts *arguments:
    node --test {{ arguments }} "src/**/*.test.ts"
