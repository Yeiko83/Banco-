"""Runner de pruebas sin pytest: `python polyphoenix/run_tests.py`."""
import traceback

from polyphoenix.tests import test_core


def main():
    funcs = [getattr(test_core, n) for n in dir(test_core) if n.startswith("test_")]
    fallos = 0
    for f in funcs:
        try:
            f()
            print(f"  PASS  {f.__name__}")
        except Exception:
            fallos += 1
            print(f"  FAIL  {f.__name__}")
            traceback.print_exc()
    print(f"\n{len(funcs) - fallos}/{len(funcs)} pruebas pasaron.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
