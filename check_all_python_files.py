import subprocess
import os

def find_python_files(root_dir):
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                py_files.append(os.path.join(dirpath, filename))
    return py_files

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    py_files = find_python_files(root)
    print(f"Checking {len(py_files)} Python files with flake8...\n")
    with open("flake8_report.txt", "w") as report:
        result = subprocess.run(['flake8'] + py_files, stdout=report, stderr=report)
    if result.returncode == 0:
        print("No issues found. See flake8_report.txt for details.")
    else:
        print("Issues detected. See flake8_report.txt for details.")
