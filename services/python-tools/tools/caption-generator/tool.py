import os
from openai import AsyncOpenAI
import asyncio
from generator import extra_text, generate_caption
from rules import MAX_RETRIES, SIMILARITY_THRESHOLD
from helper import check_variations

MANIFEST = {
    "id": "caption-generator",
    "name": "Social Media Captions",
    "description": "Describe your content and get platform-optimized captions with hashtags for Instagram, Twitter/X, LinkedIn, and more.",
    "author": "Oxlo Team",
    "version": "2.0.0",
}

async def run(data:dict)->dict:
    prompt = data.get("prompt", "")
    image_data = data.get("image", "")
    platform = data.get("platform", "linkedin").lower()
    api_key = os.getenv("OXLO_API_KEY")

    if not api_key:
        return {
            "error": "Please enter your Oxlo API key.",
            "result": None
        }

    if not prompt:
        return {
            "error": "Please enter prompt for captions.",
            "result": None
        }

    client = AsyncOpenAI(
        base_url="https://api.oxlo.ai/v1",
        api_key=api_key,
    )

    #text from image
    context_from_image = ""
    if image_data:
        context_from_image = await extra_text(image_data, api_key)

    platforms = [platform] if platform != "all" else ["twitter", "linkedin", "instagram", "youtube", "tiktok"]

    all_results = {}
    for p in platforms:
        captions = []
        retry_count = 0
        while len(captions) < 3 and retry_count <= MAX_RETRIES:
            # Generate captions
            new_captions = await asyncio.gather(
                generate_caption(client, prompt, p, "professional", context_from_image),
                generate_caption(client, prompt, p, "casual", context_from_image),
                generate_caption(client, prompt, p, "bold", context_from_image),
            )

            similarities = check_variations(new_captions)

            high_similarity_pairs = [(i, j, s) for i, j, s in similarities if s > SIMILARITY_THRESHOLD]

            if high_similarity_pairs and retry_count < MAX_RETRIES:
                regenerate_indices = set()
                for i, j, s in high_similarity_pairs:
                    regenerate_indices.add(i)
                    regenerate_indices.add(j)

                #have non-similar captions, regenerate others
                captions = [c for idx, c in enumerate(new_captions) if idx not in regenerate_indices]

                for idx in regenerate_indices:
                    style_map = {0: "professional", 1: "casual", 2: "bold"}
                    new_cap = await generate_caption(client, prompt, p, style_map[idx], context_from_image)
                    captions.append(new_cap)

                retry_count += 1
            else:
                captions = new_captions
                break
        
    return {"result": "", "metadata": {}}
