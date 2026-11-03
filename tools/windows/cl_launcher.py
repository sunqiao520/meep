"""Normalize localized MSVC /showIncludes output for Ninja's UTF-8 parser."""
import subprocess
import sys

result = subprocess.run(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    output = result.stdout.decode("utf-8")
except UnicodeDecodeError:
    output = result.stdout.decode("mbcs", errors="replace")
output = output.replace("注意: 包含文件:", "Note: including file:")
sys.stdout.buffer.write(output.encode("utf-8"))
raise SystemExit(result.returncode)
