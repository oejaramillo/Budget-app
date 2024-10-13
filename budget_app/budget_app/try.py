from pathlib import Path
import environ
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path('__file__').resolve().parent.parent.parent
print(BASE_DIR,'\n')

# Initialise environment variables
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
print("BASE_DIR:", BASE_DIR)  # Print the base directory path
print("Trying to load .env from:", os.path.join(BASE_DIR, '.env'))  # Ensure the correct path is used
#print(env('SECRET_KEY'))

env.read_env(os.path.join(BASE_DIR, '.env'))  # Load .env
#print("Environment variables loaded:", env.ENVIRON)  # Print loaded environment variables