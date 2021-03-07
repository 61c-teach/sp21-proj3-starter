#!/usr/bin/env python3

from pathlib import Path
import argparse
import csv
import os
import signal
import subprocess
import sys
import time
import traceback


proj_dir_path = Path(__file__).parent
tests_dir_path = proj_dir_path / "tests"
logisim_path = proj_dir_path / "tools" / "logisim"

tools_env = os.environ.copy()
tools_env["CS61C_TOOLS_ARGS"] = tools_env.get("CS61C_TOOLS_ARGS", "") + " -q"


class TestCase():
  def __init__(self, circ_path, name=None):
    self.circ_path = Path(circ_path)
    self.id = str(circ_path)
    self.name = name or circ_path.stem

  def can_pipeline(self):
    if self.circ_path.match("alu/*.circ") or self.circ_path.match("regfile/*.circ"):
      return False
    return True

  def get_actual_table_path(self):
    return self.circ_path.parent / "student-output" / f"{self.name}-student.out"

  def get_expected_table_path(self, pipelined=False):
    path = self.circ_path.parent / "reference-output" / f"{self.name}-ref.out"
    if pipelined:
      path = path.with_name(f"{self.name}-pipelined-ref.out")
    return path

  def run(self, pipelined=False):
    if pipelined and not self.can_pipeline():
      pipelined = False
    passed = False
    proc = None
    try:
      proc = subprocess.Popen([sys.executable, str(logisim_path), "-tty", "table,binary,csv", str(self.circ_path)], stdout=subprocess.PIPE, encoding="utf-8", errors="ignore", env=tools_env)

      with self.get_expected_table_path(pipelined=pipelined).open("r", encoding="utf-8", errors="ignore") as expected_file:
        passed = self.check_output(proc.stdout, expected_file)
        kill_proc(proc)
        if passed:
          return (True, "Matched expected output")
        else:
          return (False, "Did not match expected output")
    except KeyboardInterrupt:
      kill_proc(proc)
      sys.exit(1)
    except:
      traceback.print_exc()
      kill_proc(proc)
    return (False, "Errored while running test")

  def check_output(self, actual_file, expected_file):
    passed = True
    actual_csv = csv.reader(actual_file)
    expected_csv = csv.reader(expected_file)
    actual_lines = []
    while True:
      actual_line = next(actual_csv, None)
      expected_line = next(expected_csv, None)
      if expected_line == None:
        break
      if actual_line != expected_line:
        passed = False
      if actual_line == None:
        break
      actual_lines.append(actual_line)
    output_path = self.get_actual_table_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as output_file:
      output_csv = csv.writer(output_file)
      for line in actual_lines:
        output_csv.writerow(line)
    return passed

def run_tests(search_paths, pipelined=False):
  circ_paths = []
  for search_path in search_paths:
    if search_path.is_file() and search_path.suffix == ".circ":
      circ_paths.append(search_path)
      continue
    for circ_path in search_path.rglob("*.circ"):
      circ_paths.append(circ_path)
  circ_paths = sorted(circ_paths)

  failed_tests = []
  passed_tests = []
  for circ_path in circ_paths:
    test = TestCase(circ_path)
    did_pass, reason = False, "Unknown test error"
    try:
      did_pass, reason = test.run(pipelined=pipelined)
    except KeyboardInterrupt:
      sys.exit(1)
    except SystemExit:
      raise
    except:
      traceback.print_exc()
    if did_pass:
      print(f"PASS: {test.id}", flush=True)
      passed_tests.append(test)
    else:
      print(f"FAIL: {test.id} ({reason})", flush=True)
      failed_tests.append(test)

  print(f"Passed {len(passed_tests)}/{len(failed_tests) + len(passed_tests)} tests", flush=True)


def kill_proc(proc):
  if proc.poll() == None:
    proc.terminate()
    for _ in range(10):
      if proc.poll() != None:
        return
      time.sleep(0.1)
  if proc.poll() == None:
    proc.kill()


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Run Logisim tests")
  parser.add_argument("test_path", help="Path to a test circuit, or a directory containing test circuits", type=Path, nargs="+")
  parser.add_argument("-p", "--pipelined", help="Check against reference output for 2-stage pipeline (when applicable)", action="store_true", default=False)
  args = parser.parse_args()

  run_tests(args.test_path, args.pipelined)
