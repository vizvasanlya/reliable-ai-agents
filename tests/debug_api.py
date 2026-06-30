import os, sys, json
sys.path.insert(0, r'E:\89P13\reliable-ai-agents\src')
from llm.provider import OpenCodeZenProvider

api_key = os.environ.get('ZEN_API_KEY')
provider = OpenCodeZenProvider(api_key=api_key, model='mimo-v2.5-free')

PLANNING_SYSTEM = """You are a software project planner. Break down requests into tasks.
Output ONLY a valid JSON array. No explanation, no markdown, no code blocks.
Format: [{"id": "T1", "description": "what to do", "tools_needed": ["write_file"], "acceptance_criteria": ["criteria"], "estimated_minutes": 10, "dependencies": []}]
"""

response = provider.complete(
    "Create a web scraper that fetches page titles",
    system=PLANNING_SYSTEM,
    temperature=0.3,
    max_tokens=2000
)

print("Raw content:")
print(response.content[:1000])
print()
print("Trying to parse as JSON...")
try:
    tasks = json.loads(response.content)
    print(f"SUCCESS: Got {len(tasks)} tasks")
    for t in tasks:
        print(f"  {t['id']}: {t['description']}")
except json.JSONDecodeError as e:
    print(f"FAILED: {e}")
    print("Response is not valid JSON")
