import sys
import os
import asyncio

# Fix path resolution for local/CI imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.services.search_service import map_deeplinks

sample_payload = {
    "contexts": [
        {"description": "Turn off adaptive brightness in display settings"},
        {"description": "Wipe the light sensor on top of the screen with a clean cloth"}
    ]
}

async def main():
    print("Testing map_deeplinks integration...")
    result = await map_deeplinks(sample_payload)
    
    print("\n--- MAPPED RESULT ---")
    for item in result.get("contexts", []):
        print(f"Description : {item.get('description')}")
        print(f"Category    : {item.get('category')}")
        print(f"Deeplink    : {item.get('actionableDeeplink')}\n")

if __name__ == "__main__":
    asyncio.run(main())
