from dotenv import load_dotenv

load_dotenv()
from langfuse import Langfuse


langfuse = Langfuse()

# Collect every prompt name in the project
names = set()
page = 1
while True:
    resp = langfuse.api.prompts.list(page=page, limit=100)
    if not resp.data:
        break
    names.update(p.name for p in resp.data)
    page += 1
    if page > resp.meta.total_pages:
        break

# Promote each one's newest version to "production"
for name in names:
    latest = langfuse.get_prompt(name, label="latest")
    langfuse.update_prompt(name=name, version=latest.version, new_labels=["production"])
    print(f"promoted {name} v{latest.version} -> production")