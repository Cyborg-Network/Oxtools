import asyncio
from openai import AsyncOpenAI
from rules import PLATFORM_RULES, VARIATION_STYLES

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

async def generate_caption(
    client: AsyncOpenAI,
    prompt: str,
    platform: str,
    style: str,
    context_from_image: str = ""
) -> str:

    platform_map = {
        "x(twitter)": "X(Twitter)",
        "instagram": "Instagram",
        "linkedin": "Linkedin",
        "youtube": "Youtube",
        "tiktok": "Tiktok"
    }
    platform_key = platform_map.get(platform, platform)
    platform_info = PLATFORM_RULES.get(platform_key, PLATFORM_RULES["Linkedin"])
    style_info = VARIATION_STYLES.get(style, VARIATION_STYLES["professional"])

    emoji_guidance = {
        "professional": "0-1 emoji only if needed, place at very end",
        "casual": "2-3 emojis, end of sentences",
        "bold": "3-5 emojis, end of sentences for impact"
    }
    
    max_chars = platform_info['max_length']
    hashtag_count = platform_info['hashtag_count']
    
    enhanced_prompt = f"""Write a natural, human-like social media caption for {platform_info['name']}. 

Write like a real person, not like an AI.

STRICT REQUIREMENTS:
- Caption (excluding hashtags): MUST be under {max_chars} characters
- Add {hashtag_count[0]}-{hashtag_count[1]} hashtags at the very end on a new line
- NEVER put emojis in middle of words/sentences - ONLY at END of complete sentences or at very end of caption
- Do NOT use em dashes (—) in the caption use regular hyphens (-) or no punctuation instead
- Write in natural, conversational way people actually use

Style ({style_info['name']}): {style_info['description']}
Emoji count: {emoji_guidance.get(style, "1-2 at end")}

Content: {prompt}"""

    if context_from_image:
        enhanced_prompt += f"\n\nAdditional context from image: {context_from_image}"

    response = await client.chat.completions.create(
        model="kimi-k2.5",
        messages=[
            {"role": "user", "content": enhanced_prompt}
        ],
        max_tokens=500,
    )

    return response.choices[0].message.content