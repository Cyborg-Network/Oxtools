import os
from openai import AsyncOpenAI
import asyncio
from generator import extra_text, generate_caption
from rules import MAX_RETRIES, SIMILARITY_THRESHOLD, PLATFORM_RULES
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
    platform = data.get("platform", "linkedin")
    platform_lower = platform.lower()
    if platform_lower == "all platform":
        platform = "all"
    else:
        platform = platform_lower
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

    words = prompt.strip().split()
    if len(words) < 5:
        return {
            "error": "Please describe your content in more detail. Add more information about what you want to share.",
            "result": None
        }
    
    random_patterns = ["asdf", "qwerty", "12345", "abc", "xxx", "yyy", "test", "ffff", "dddd"]
    lower_prompt = prompt.lower()
    if len(words) < 10 and any(p in lower_prompt for p in random_patterns):
        return {
            "error": "Please describe your content in more detail. Add more information about what you want to share.",
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

    platform_map = {
        "twitter": "X(Twitter)",
        "instagram": "Instagram",
        "linkedin": "Linkedin",
        "youtube": "Youtube",
        "tiktok": "Tiktok"
    }
    platforms = [platform] if platform != "all" else list(platform_map.keys())
    platform_keys = [platform_map.get(p, p.capitalize()) for p in platforms]

    all_results = {}
    for p, p_key in zip(platforms, platform_keys):
        captions = []
        retry_count = 0
        while len(captions) < 3 and retry_count <= MAX_RETRIES:
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

                captions = [c for idx, c in enumerate(new_captions) if idx not in regenerate_indices]

                for idx in regenerate_indices:
                    style_map = {0: "professional", 1: "casual", 2: "bold"}
                    new_cap = await generate_caption(client, prompt, p, style_map[idx], context_from_image)
                    captions.append(new_cap)

                retry_count += 1
            else:
                captions = new_captions
                break
        
        all_results[p_key] ={"variations": captions, "similarities": similarities, "retries": retry_count}
    
    output_lines = []

    # if context_from_image:
    #     output_lines.append(f"[Image OCR: {context_from_image[:100]}...]")
    #     output_lines.append("")

    for p, platform_data in all_results.items():
        plat_info = PLATFORM_RULES.get(p, {})
        plat_name = plat_info.get("name", p.upper())
        output_lines.append(f"\n**{plat_name}**\n")
        output_lines.append(f"Character limit: {plat_info.get('max_length', 'N/A')}")
        output_lines.append(f"Hashtags: {plat_info.get('hashtag_count', 'N/A')}")
        output_lines.append("")
        
        variations = platform_data.get("variations", [])
        style_names = ["Professional", "Casual", "Bold"]
        for i, caption in enumerate(variations):
            output_lines.append(f"**{style_names[i]}**")
            output_lines.append("")
            output_lines.append(caption)
            output_lines.append("")
    
    return {"result": "\n".join(output_lines), 
            "metadata": {
                "platforms":platforms,
                "has_ocr": bool(context_from_image),
                "captions_data": all_results
            }
    }



