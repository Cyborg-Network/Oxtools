import re
import asyncio
from openai import AsyncOpenAI
from rules import PLATFORM_LIMITS, PLATFORM_REVERSE_MAP, get_limits


def sanitize_output(text: str) -> str:
    text = text.replace("\\n", "\n")
    text = re.sub(r'-{2,}', '-', text)
    text = re.sub(r'—', '-', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text

async def extra_text(image_data:str, api_key: str) ->str:
    if not image_data:
        return ""
    
    client = AsyncOpenAI(
        base_url="https://api.oxlo.ai/v1",
        api_key=api_key
    )
    
    try:
        response = await client.chat.completions.create(
            model="kimi-k2.5",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all visible text from this image. Return only the text content, nothing else."},
                        {"type": "image_url", "image_url": {"url": image_data}}
                    ]
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"OCR error: {e}")
        return ""

def build_prompt(platform: str,length_type: str, prompt: str, context_from_image: str = "") -> str:
    plat = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["linkedin"])
    limits = get_limits(platform, length_type)
    
    is_short = length_type == "short"
    is_reddit = platform == "reddit"
    title_optional = plat.get("title_optional", True)
    has_title = (plat.get("title_max", 0) > 0 and title_optional) or "title_short_min" in plat
    
    style_guides = {
        "engaging_informative": "engaging, informative, YouTube-friendly. Hook viewers in the first line. Clear and conversational.",
        "punchy_short_form": "punchy, fast-paced, hook-first. Perfect for short attention spans. Bold and energetic.",
        "trending_energetic": "trending, energetic, TikTok-native. Use popular phrases naturally. Fun and relatable.",
        "visual_storytelling": "visual-friendly, storytelling-focused. Complement the image/video. Emotional and engaging.",
        "authentic_community": "authentic, community-focused, Reddit-native. No clickbait. Honest and direct.",
        "professional_thoughtful": "professional, thought-provoking, LinkedIn-appropriate. No emojis or minimal. Value-driven.",
        "concise_punchy": "concise, punchy, hook-first. Every word counts. Bold and direct.",
    }
    style_guide = style_guides.get(plat.get("style", "concise_punchy"), "concise and engaging")
    
    emoji_count = plat.get("emoji_limit", (1, 3))
    emoji_guide = f"Use {emoji_count[0]}-{emoji_count[1]} emojis, placed at the end of sentences or at the very end of the caption."
    if plat.get("style") == "professional_thoughtful":
        emoji_guide = "Use 0-1 emoji only if truly needed, or skip emojis entirely."
    
    cta_patterns = plat.get("cta_patterns", [])
    cta_text = ", ".join(cta_patterns[:3])
    
    hashtag_count = plat.get("hashtag_count", (3, 5))
    if hashtag_count[1] == 0:
        hashtag_text = "Do NOT use any hashtags."
    else:
        hashtag_text = f"Add {hashtag_count[0]}-{hashtag_count[1]} relevant hashtags at the end on a new line."
    
    word_limits = {
        "youtube": {"short": 30, "long": 60},
        "youtube_shorts": {"short": 15, "long": 25},
        "tiktok": {"short": 15, "long": 25},
        "instagram": {"short": 15, "long": 25},
        "reddit": {"short": 100, "long": 200},
        "linkedin": {"short": 100, "long": 200},
        "x_twitter": {"short": 50, "long": 100}
    }
    max_words = word_limits.get(platform, {}).get(length_type, 25)

    if is_reddit:
        title_min = limits.get("title_min", 50)
        title_max = limits.get("title_max", 120)
        caption_min = limits.get("caption_min", 500)
        caption_max = limits.get("caption_max", 1000)
        
        prompt_text = f"""Create 3 Reddit posts with different titles.

Write 3 posts:
Title 1: [title {title_min}-{title_max} chars]
Description 1: [post {caption_min}-{caption_max} chars, {max_words} words max]

Title 2: [different title]
Description 2: [different post]

Title 3: [different title]
Description 3: [different post]

Rules:
- All 3 titles must use different words
- Use line breaks in body
- End each with a question
- {emoji_guide}

Topic: {prompt}"""
        
        if context_from_image:
            prompt_text += f"\n\nAdditional context from image: {context_from_image}"
        
        return prompt_text
    
    elif has_title:
        title_max_val = plat.get("title_max", 60)
        caption_min = limits.get("caption_min", 60)
        caption_max = limits.get("caption_max", 100)
        
        prompt_text = f"""Create 3 YouTube video captions with different titles.

Write 3 posts:
Title 1: [title max {title_max_val} chars]
Description 1: [caption {caption_min}-{caption_max} chars, {max_words} words max - make it detailed and engaging]

Title 2: [different title]
Description 2: [different caption]

Title 3: [different title]
Description 3: [different caption]

Rules:
- All 3 titles must use different words/angles
- Don't repeat same title words
- Descriptions should be {caption_min}-{caption_max} characters - write close to the max
- {hashtag_text}
- {cta_text}
- {emoji_guide}

Topic: {prompt}"""
        
        if context_from_image:
            prompt_text += f"\n\nAdditional context from image: {context_from_image}"
        
        return prompt_text
    
    else:
        caption_min = limits.get("caption_min", 100)
        caption_max = limits.get("caption_max", 280)
        
        prompt_text = f"""Write a natural, human-like social media caption.

Platform: {plat['name']}
Style: {style_guide}

Write EXACTLY {caption_min}-{caption_max} characters.

Requirements:
- Hook viewers in the first line - this is the most important part
- Be engaging, {style_guide}
- {hashtag_text}
- {cta_text}
- {emoji_guide}
- Do NOT use double dashes (--) or em dashes (---) - use a single hyphen (-) instead
- Write like a real person, not like an AI
- MAXIMUM {max_words} WORDS

User's topic: {prompt}"""
        
        if context_from_image:
            prompt_text += f"\n\nAdditional context from image: {context_from_image}"
        
        return prompt_text


async def generate_caption(
    client: AsyncOpenAI,
    prompt: str,
    platform: str,
    length_type: str,
    context_from_image: str = ""
) -> str:
    enhanced_prompt = build_prompt(platform, length_type, prompt, context_from_image)
    
    plat = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["linkedin"])
    limits = get_limits(platform, length_type)
    max_tokens = min(limits.get("caption_max", 280) // 4, 500)
    
    response = await client.chat.completions.create(
        model="kimi-k2.5",
        messages=[
            {
                "role": "system",
                "content": f"You are a social media caption writing assistant. Return ONLY the caption text - no explanations, no markdown formatting, no extra text. CRITICAL: The caption must be EXACTLY between {limits.get('caption_min', 50)} and {limits.get('caption_max', 100)} characters. NEVER exceed {limits.get('caption_max', 100)} characters. Do not use double dashes (--) or em dashes (---). Use a single hyphen (-) instead."
            },
            {"role": "user", "content": enhanced_prompt}
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    
    return response.choices[0].message.content or ""


async def generate_all_captions(
    client: AsyncOpenAI,
    prompt: str,
    platform: str,
    length_type: str,
    context_from_image: str = ""
) -> dict:
    plat = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["linkedin"])
    limits = get_limits(platform, length_type)
    is_reddit = platform == "reddit"
    
    variations = await asyncio.gather(
        generate_caption(client, prompt, platform, length_type, context_from_image),
        generate_caption(client, prompt, platform, length_type, context_from_image),
        generate_caption(client, prompt, platform, length_type, context_from_image),
    )
    
    results = []
    titles = []
    title_optional = plat.get("title_optional", True)
    has_title = (plat.get("title_max", 0) > 0 and title_optional) or "title_short_min" in plat
    
    all_variations_text = []
    for variation in variations:
        if variation:
            text = sanitize_output(variation.strip())
            parts = re.split(r'(?:Title\s*\d*:)|(?:Description\s*\d*:)|(?:Option\s*[123]:)|(?:\d+\.)|(?:---)', text, flags=re.IGNORECASE)
            found_parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]
            if len(found_parts) >= 3:
                all_variations_text.extend(found_parts[:3])
            else:
                all_variations_text.append(text)

    for text in all_variations_text[:3]:
        var_title = None
        
        if has_title or is_reddit:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            title_pattern = re.search(r'(?:Title\s*\d*[\s:]*)', text, re.IGNORECASE)
            if title_pattern:
                start = title_pattern.end()
                remaining = text[start:].strip()
                newline_pos = remaining.find("\n")
                if newline_pos > 0:
                    potential_title = remaining[:newline_pos].strip()
                else:
                    potential_title = remaining.strip()
                
                title_limit = plat.get("title_max", 60)
                if is_reddit:
                    title_limit = limits.get("title_max", 120)
                if potential_title and len(potential_title) <= title_limit:
                    var_title = potential_title
                    after_title = remaining[newline_pos:] if newline_pos > 0 else ""
                    text = after_title.strip()
            
            if not var_title and lines:
                first_line = lines[0]
                title_limit = plat.get("title_max", 60)
                if is_reddit:
                    title_limit = limits.get("title_max", 120)
                if len(first_line) <= title_limit and not first_line.startswith("#"):
                    var_title = first_line
                    text = " ".join(lines[1:]) if len(lines) > 1 else ""
            
            text = re.sub(r'^(?:Description\s*\d*:)\s*', '', text, flags=re.IGNORECASE).strip()
            
            caption_text = text
        else:
            caption_text = text
        
        caption_limit = limits.get("caption_max", 280)
        
        if len(caption_text) > caption_limit:
            caption_text = caption_text[:caption_limit]
            last_space = caption_text.rfind(" ")
            if last_space > 0:
                caption_text = caption_text[:last_space]
            caption_text = caption_text.strip()
        
        if len(caption_text) > caption_limit:
            caption_text = caption_text[:caption_limit]
        
        results.append({
            "text": caption_text,
            "chars": len(caption_text),
            "limit": caption_limit,
            "title": var_title,
        })
        if var_title:
            titles.append(var_title)
    
    for i, r in enumerate(results):
        if i < len(titles):
            r["title"] = titles[i]
    
    main_title = titles[0] if titles else None
    
    return {
        "title": main_title,
        "titles": titles,
        "variation_type": length_type,
        "platform": plat.get("name", platform),
        "variations": results,
    }