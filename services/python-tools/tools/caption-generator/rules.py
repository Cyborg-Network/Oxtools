# platform rules and variation for posts


PLATFORM_RULES = {
    "X(Twitter)": {
        "name": "X (Twitter)",
        "max_length": 280,
        "hashtag_count": (2, 3),
        "cta_patterns": ["Link in bio", "Click the link", "Learn more", "Read more"],
        "emoji_limit": (1, 3)
    },
    "Instagram": {
        "name": "Instagram",
        "max_length": 2200,
        "hashtag_count": (5, 8),
        "cta_patterns": ["Double tap if you agree", "Tag someone", "Share with a friend", "Link in bio"],
        "emoji_limit": (3, 6)
    },
    "Linkedin": {
        "name": "LinkedIn",
        "max_length": 3000,
        "hashtag_count": (3, 5),
        "cta_patterns": ["What are your thoughts?", "Share your experience", "Let's connect", "Comments welcome"],
        "emoji_limit": (2, 5)
    },
    "Youtube": {
        "name": "YouTube",
        "max_length": 5000,
        "hashtag_count": (3, 5),
        "cta_patterns": ["Like and subscribe", "Let me know in comments", "Share your thoughts", "Don't forget to subscribe"],
        "emoji_limit": (1, 3)
    },
    "Tiktok": {
        "name": "TikTok",
        "max_length": 2200,
        "hashtag_count": (3, 5),
        "cta_patterns": ["Follow for more", "Like and follow", "Duet this", "Share with friends"],
        "emoji_limit": (2, 5)
    },
}

VARIATION_STYLES = {
    "professional": {
        "name": "Professional",
        "description": "Formal, polished, business-appropriate tone",
        "characteristics": ["Clear and concise", "Professional vocabulary", "Minimal emoji", "Structured"]
    },
    "casual": {
        "name": "Casual",
        "description": "Friendly, conversational, approachable tone",
        "characteristics": ["Warm language", "Light emoji", "Conversational", "Engaging"]
    },
    "bold": {
        "name": "Bold",
        "description": "Confident, attention-grabbing, high-impact tone",
        "characteristics": ["Power words", "Strong statements", "More emoji", "Call to action"]
    },
}

MAX_RETRIES = 2
SIMILARITY_THRESHOLD = 0.70