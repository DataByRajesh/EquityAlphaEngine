import os
import re
import subprocess

SEVERITY_MAP = {
    "E": "Error",
    "F": "Fatal",
    "W": "Warning",
    "C": "Convention",
    "N": "Naming",
}


def find_python_files(root_dir):
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                py_files.append(os.path.join(dirpath, filename))
    return py_files


def categorize_flake8_output(lines):
    categorized = []
    pattern = re.compile(r"^(.*?):(\d+):(\d+): ([A-Z]\d{3}) (.*)$")
    for line in lines:
        match = pattern.match(line)
        if match:
            file, lineno, col, code, msg = match.groups()
            severity = SEVERITY_MAP.get(code[0], "Other")
            categorized.append(
                f"[{severity}] {file}:{lineno}:{col}: {code} {msg}")
        else:
            categorized.append(line)
    return categorized


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    py_files = find_python_files(root)
    print(
        f"Formatting {
            len(py_files)} Python files with black, isort, and autopep8...\n"
    )
    # Run black
    subprocess.run(["black"] + py_files)
    # Run isort
    subprocess.run(["isort"] + py_files)
    # Run autopep8
    subprocess.run(["autopep8", "--in-place", "--recursive", root])
    print(f"Checking {len(py_files)} Python files with flake8...\n")
    result = subprocess.run(["flake8"] + py_files,
                            capture_output=True, text=True)
    lines = result.stdout.splitlines() + result.stderr.splitlines()
    categorized = categorize_flake8_output(lines)
    with open("flake8_report.txt", "w") as report:
        for line in categorized:
            report.write(line + "\n")
    if result.returncode == 0:
        print("No issues found. See flake8_report.txt for details.")
    else:
        print("Issues detected. See flake8_report.txt for details.")
