import asyncio
from openai import AsyncOpenAI
from rules import PLATFORM_RULES, VARIATION_STYLES

async def extra_text(image_data:str, api_key: str) ->str:
    client = AsyncOpenAI(
        base_url="https://api.oxlo.ai/v1",
        api_key=api_key
    )

async def generate_caption(
    client: AsyncOpenAI,
    prompt: str,
    platform: str,
    style: str,
    context_from_image: str = ""
) -> str:

    platform_info = PLATFORM_RULES.get(platform, PLATFORM_RULES["linkedin"])
    style_info = VARIATION_STYLES.get(style, VARIATION_STYLES["professional"])

    enhanced_prompt = f"""Generate a {style} social media caption for {platform_info['name']}.

Requirements:
- Maximum {platform_info['max_length']} characters
- Use {platform_info['hashtag_count'][0]}-{platform_info['hashtag_count'][1]} relevant hashtags
- Include 1-2 emojis appropriate for the platform
- Add a clear call-to-action from these options: {', '.join(platform_info['cta_patterns'])}
- Style: {style_info['description']}
- Characteristics: {', '.join(style_info['characteristics'])}

User's original prompt: {prompt}"""

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