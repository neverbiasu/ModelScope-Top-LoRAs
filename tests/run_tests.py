"""
Run pytest and save results into tests/results/results.xml (junit xml).

Usage:
    python tests/run_tests.py

This script will create `tests/results/` and invoke pytest programmatically to
write a JUnit-style XML report to `tests/results/results.xml`.
"""
import os
from pathlib import Path
import sys

import pytest


def main():
    results_dir = Path(__file__).parent / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    xml_path = results_dir / 'results.xml'

    # Run pytest and write junit xml
    # Using -q for quieter output; remove if verbose output desired
    args = ['-q', f'--junitxml={xml_path}', str(Path(__file__).parent)]
    print('Running pytest with args:', args)
    ret = pytest.main(args)
    print('pytest exit code:', ret)
    if ret != 0:
        sys.exit(ret)


if __name__ == '__main__':
    main()
