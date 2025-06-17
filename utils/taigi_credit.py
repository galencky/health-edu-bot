"""Taigi TTS credit bubble generator"""

def create_taigi_credit_bubble():
    """
    Create a LINE Flex Message bubble for NYCU's Taigi TTS credit
    """
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🇹🇼 台語語音技術提供",
                    "weight": "bold",
                    "size": "md",
                    "color": "#000000"
                },
                {
                    "type": "text",
                    "text": "Credit: NYCU's Taigi TTS",
                    "size": "sm",
                    "color": "#3366CC",
                    "action": {
                        "type": "uri",
                        "uri": "http://tts001.iptcloud.net:8804/"
                    },
                    "margin": "sm",
                    "decoration": "underline"
                }
            ],
            "spacing": "sm",
            "paddingAll": "13px"
        },
        "styles": {
            "body": {
                "backgroundColor": "#F0F0F0"
            }
        }
    }