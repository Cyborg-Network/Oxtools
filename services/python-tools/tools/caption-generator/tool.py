import os
import re
from openai import AsyncOpenAI
import asyncio
from generator import extra_text, generate_all_captions
from rules import PLATFORM_LIMITS, PLATFORM_REVERSE_MAP
from helper import check_variations

MANIFEST = {
    "id": "caption-generator",
    "name": "Social Media Captions",
    "description": "Generate platform-optimized captions with hashtag suggestions for YouTube, TikTok, Instagram, LinkedIn, Reddit, and X/Twitter.",
    "author": "Oxlo Team",
    "version": "3.0.0",
}

MAX_RETRIES = 2
SIMILARITY_THRESHOLD = 0.70


def normalize_platform(platform: str) -> str:
    if not platform:
        return "linkedin"
    
    platform_lower = platform.lower().strip()
    
    direct_map = {
        "youtube": "youtube",
        "youtube_shorts": "youtube_shorts",
        "youtube shorts": "youtube_shorts",
        "tiktok": "tiktok",
        "instagram": "instagram",
        "reddit": "reddit",
        "linkedin": "linkedin",
        "x": "x_twitter",
        "x_twitter": "x_twitter",
        "x(twitter)": "x_twitter",
        "twitter": "x_twitter",
    }
    
    if platform_lower in direct_map:
        return direct_map[platform_lower]
    
    if platform in PLATFORM_REVERSE_MAP:
        return PLATFORM_REVERSE_MAP[platform]
    
    for key in PLATFORM_LIMITS.keys():
        if key in platform_lower or platform_lower in key:
            return key
    
    return "linkedin"


def validate_length_type(length_type: str) -> str:
    if length_type and length_type.lower() in ["short", "long"]:
        return length_type.lower()
    return "short"


async def run(data: dict) -> dict:
    prompt = data.get("prompt", "")
    platform_input = data.get("platform", "linkedin")
    length_type_input = data.get("length_type", "short")
    image_data = data.get("image", "")

    import logging
    logger = logging.getLogger("caption-generator")
    logger.info(f"Received request: platform={platform_input}, length={length_type_input}, prompt_len={len(prompt)}, has_image={bool(image_data)}")
    
    platform = normalize_platform(platform_input)
    length_type = validate_length_type(length_type_input)
    
    api_key = os.getenv("OXLO_API_KEY")

    if not api_key:
        logger.error("No OXLO_API_KEY set")
        return {
            "error": "Please enter your Oxlo API key.",
            "result": None
        }

    if not prompt:
        logger.error("Empty prompt")
        return {
            "error": "Please enter a prompt for captions.",
            "result": None
        }

    words = prompt.strip().split()
    if len(words) < 5:
        logger.error(f"Prompt too short: {len(words)} words")
        return {
            "error": "Please describe your content in more detail. Add more information about what you want to share.",
            "result": None
        }
    
    random_patterns = ["asdf", "qwerty", "12345", "abc", "xxx", "yyy", "test", "ffff", "dddd"]
    lower_prompt = prompt.lower()
    if len(words) < 10 and any(p in lower_prompt for p in random_patterns):
        logger.error("Random pattern detected in prompt")
        return {
            "error": "Please describe your content in more detail. Add more information about what you want to share.",
            "result": None
        }

    client = AsyncOpenAI(
        base_url="https://api.oxlo.ai/v1",
        api_key=api_key,
    )

    context_from_image = ""
    if image_data:
        logger.info("Extracting text from image")
        context_from_image = await extra_text(image_data, api_key)
        logger.info(f"Image OCR result: {len(context_from_image)} chars")

    plat_info = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["linkedin"])
    logger.info(f"Generating captions for {platform} ({length_type})")
    
    all_results = []
    retry_count = 0
    
    while len(all_results) < 3 and retry_count <= MAX_RETRIES:
        logger.info(f"Generation attempt {retry_count + 1}")
        new_results = await asyncio.gather(
            generate_all_captions(client, prompt, platform, length_type, context_from_image),
            generate_all_captions(client, prompt, platform, length_type, context_from_image),
            generate_all_captions(client, prompt, platform, length_type, context_from_image),
        )
        
        new_variations = [r.get("variations", []) for r in new_results]
        
        flat_captions = []
        for variation_set in new_variations:
            for v in variation_set:
                flat_captions.append(v.get("text", ""))
        
        if len(flat_captions) >= 3:
            similarities = check_variations(flat_captions)
            high_similarity_pairs = [(i, j, s) for i, j, s in similarities if s > SIMILARITY_THRESHOLD]
            
            if high_similarity_pairs and retry_count < MAX_RETRIES:
                retry_count += 1
                continue
        
        all_results = new_results
        break

    plat_name = plat_info.get("name", platform.capitalize())
    
    output_lines = []
    
    title = None
    for r in all_results:
        if r.get("title"):
            t = r.get("title", "")
            t = re.sub(r'\*\*', '', t)
            t = re.sub(r'-{2,}', '-', t)
            t = re.sub(r'—', '-', t)
            t = t.strip()
            title = t
            break
    
    variations_output = []
    for result in all_results:
        for variation in result.get("variations", []):
            text = variation.get("text", "")
            if not text:
                continue
            text = re.sub(r'\*\*', '', text)
            text = re.sub(r'-{2,}', '-', text)
            text = re.sub(r'—', '-', text)
            text = text.replace("\\n", "\n")
            text = re.sub(r'^[#*>\s]+', '', text, flags=re.MULTILINE)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            if text:
                variations_output.append({
                    "text": text,
                    "chars": len(text),
                    "limit": variation.get("limit", 280),
                    "title": variation.get("title", ""),
                })
    
    logger.info(f"Title: {title}")
    logger.info(f"Variations generated: {len(variations_output)}")
    if variations_output:
        logger.info(f"First variation chars: {variations_output[0]['chars']}")
    
    for i, v in enumerate(variations_output[:3], 1):
        if v.get("title"):
            output_lines.append(v["title"])
            output_lines.append("")
        output_lines.append(f"Variation {i} - Description:")
        output_lines.append(v["text"])
        output_lines.append(f"[{v['chars']}/{v['limit']} chars]")
        output_lines.append("")

    return {
        "result": "\n".join(output_lines),
        "metadata": {
            "platform": platform,
            "platform_name": plat_name,
            "length_type": length_type,
            "variation_type": length_type,
            "has_image_context": bool(context_from_image),
        },
        "title": title,
        "variations": variations_output[:3],
    }