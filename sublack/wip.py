import subprocess


a = 1 + 1
result = subprocess.run(["taskkill", "/F", "/T", "/PID", "2728"], capture_output=True)
print(result.stdout)
print(result.stderr)
