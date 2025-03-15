from os.path import isfile
import subprocess
import sys
Import("env")

python = sys.executable


def escape_chars(input_string):
    escaped_string = input_string.replace('"', r'\"').replace("'", r"\'")
    print(escaped_string)
    return escaped_string


try:
    print("Installing python dotenv")
    subprocess.check_call([python, '-m', 'pip', '--version'])
    subprocess.check_call([python, '-m', 'pip', 'install', 'python-dotenv'])

except Exception:
    print("Something went wrong when installing")

assert isfile(".env")
try:
  f = open(".env", "r")
  lines = f.readlines()
  envs = []
  for line in lines:
    line = line.strip()
    pieces = line.split("=")
    print(pieces)
    envs.append("-D " + pieces[0] + "=" + "'\"{}\"'".format(escape_chars(pieces[1])))
  env.Append(BUILD_FLAGS=envs)
except IOError:
  print("File .env not accessible",)
finally:
  f.close()