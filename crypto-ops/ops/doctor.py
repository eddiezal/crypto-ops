import platform, os
from libs.dotenv_min import load_dotenv
from libs.notion_client_min import check_database

load_dotenv()

print("Python:", platform.python_version())
print("NOTION_TOKEN:", "SET" if os.getenv("NOTION_TOKEN") else "MISSING")
print("RUNS DB:", os.getenv("NOTION_RUNS_DB","MISSING"))
print("SNAPSHOTS DB:", os.getenv("NOTION_SNAPSHOTS_DB","MISSING"))
if os.getenv("NOTION_TOKEN") and os.getenv("NOTION_RUNS_DB"):
    check_database(os.getenv("NOTION_RUNS_DB"))
if os.getenv("NOTION_TOKEN") and os.getenv("NOTION_SNAPSHOTS_DB"):
    check_database(os.getenv("NOTION_SNAPSHOTS_DB"))
