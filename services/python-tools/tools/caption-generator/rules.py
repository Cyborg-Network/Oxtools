# platform-specific character limits and caption generation rules

PLATFORM_LIMITS = {
    "youtube": {
        "name": "YouTube",
        "caption_short_min": 60,
        "caption_short_max": 100,
        "caption_long_min": 150,
        "caption_long_max": 200,
        "title_max": 60,
        "title_optional": True,
        "hashtag_count": (3, 5),
        "cta_patterns": ["Like and subscribe", "Let me know in comments", "Share your thoughts", "Don't forget to subscribe"],
        "style": "engaging_informative",
        "emoji_limit": (1, 3),
    },
    "youtube_shorts": {
        "name": "YouTube Shorts",
        "caption_short_min": 40,
        "caption_short_max": 60,
        "caption_long_min": 80,
        "caption_long_max": 100,
        "title_max": 40,
        "title_optional": True,
        "hashtag_count": (2, 3),
        "cta_patterns": ["Follow for more", "Like if you enjoyed", "Share with friends"],
        "style": "punchy_short_form",
        "emoji_limit": (1, 2),
    },
    "tiktok": {
        "name": "TikTok",
        "caption_short_min": 50,
        "caption_short_max": 80,
        "caption_long_min": 100,
        "caption_long_max": 150,
        "title_max": 35,
        "title_optional": False,
        "hashtag_count": (3, 5),
        "cta_patterns": ["Follow for more", "Duet this", "Share with friends", "Save this"],
        "style": "trending_energetic",
        "emoji_limit": (2, 5),
    },
    "instagram": {
        "name": "Instagram",
        "caption_short_min": 80,
        "caption_short_max": 100,
        "caption_long_min": 125,
        "caption_long_max": 150,
        "title_max": 0,
        "title_optional": False,
        "hashtag_count": (3, 5),
        "cta_patterns": ["Double tap if you agree", "Tag someone", "Share with a friend", "Link in bio"],
        "style": "visual_storytelling",
        "emoji_limit": (3, 6),
    },
    "reddit": {
        "name": "Reddit",
        "title_short_min": 60,
        "title_short_max": 120,
        "title_long_min": 120,
        "title_long_max": 200,
        "caption_short_min": 500,
        "caption_short_max": 1000,
        "caption_long_min": 1000,
        "caption_long_max": 2000,
        "hashtag_count": (0, 0),
        "cta_patterns": ["What do you think?", "Share your experience", "Comments welcome"],
        "style": "authentic_community",
        "emoji_limit": (0, 1),
    },
    "linkedin": {
        "name": "LinkedIn",
        "caption_short_min": 150,
        "caption_short_max": 300,
        "caption_long_min": 600,
        "caption_long_max": 2000,
        "title_max": 0,
        "title_optional": False,
        "hashtag_count": (3, 5),
        "cta_patterns": ["What are your thoughts?", "Share your experience", "Let's connect", "Comments welcome"],
        "style": "professional_thoughtful",
        "emoji_limit": (0, 2),
    },
    "x_twitter": {
        "name": "X (Twitter)",
        "caption_short_min": 100,
        "caption_short_max": 140,
        "caption_long_min": 200,
        "caption_long_max": 280,
        "title_max": 0,
        "title_optional": False,
        "hashtag_count": (2, 3),
        "cta_patterns": ["Link in bio", "Click the link", "Quote this", "Repost"],
        "style": "concise_punchy",
        "emoji_limit": (1, 3),
    },
}

# Platform mapping for frontend values
PLATFORM_KEYS = {
    "youtube": "youtube",
    "youtube_shorts": "youtube_shorts",
    "tiktok": "tiktok",
    "instagram": "instagram",
    "reddit": "reddit",
    "linkedin": "linkedin",
    "x_twitter": "x_twitter",
}

# Reverse mapping from display names
PLATFORM_REVERSE_MAP = {
    "YouTube": "youtube",
    "YouTube Shorts": "youtube_shorts",
    "TikTok": "tiktok",
    "Instagram": "instagram",
    "Reddit": "reddit",
    "LinkedIn": "linkedin",
    "X (Twitter)": "x_twitter",
    "X(Twitter)": "x_twitter",
}

def get_limits(platform: str, length_type: str) -> dict:
    plat = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["linkedin"])
    is_short = length_type == "short"
    
    title_optional = plat.get("title_optional", True)
    has_title = (plat.get("title_max", 0) > 0 and title_optional) or "title_short_min" in plat
    is_title_only = "title_short_min" in plat
    
    if is_title_only:
        return {
            "title_min": plat["title_short_min"] if is_short else plat["title_long_min"],
            "title_max": plat["title_short_max"] if is_short else plat["title_long_max"],
            "caption_min": plat["caption_short_min"] if is_short else plat["caption_long_min"],
            "caption_max": plat["caption_short_max"] if is_short else plat["caption_long_max"],
        }
    
    if has_title:
        return {
            "caption_min": plat["caption_short_min"] if is_short else plat["caption_long_min"],
            "caption_max": plat["caption_short_max"] if is_short else plat["caption_long_max"],
            "title_max": plat["title_max"],
        }
    
    return {
        "caption_min": plat["caption_short_min"] if is_short else plat["caption_long_min"],
        "caption_max": plat["caption_short_max"] if is_short else plat["caption_long_max"],
    }