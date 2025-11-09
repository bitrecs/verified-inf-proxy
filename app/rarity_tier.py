from enum import Enum

class RarityTier(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    UNIQUE = "Unique"
    LEGENDARY = "Legendary"


    @staticmethod
    def get_tier_icon(tier: 'RarityTier') -> str:
        """Return a colored Unicode icon for the tier using ANSI escape codes."""
        icons = {
            RarityTier.COMMON: "\033[90m●\033[0m",          # Gray circle
            RarityTier.UNCOMMON: "\033[32m●\033[0m",        # Green circle
            RarityTier.RARE: "\033[34m●\033[0m",            # Blue circle
            RarityTier.EPIC: "\033[35m●\033[0m",            # Purple circle
            RarityTier.UNIQUE: "\033[33m♦\033[0m",          # Yellow diamond
            RarityTier.LEGENDARY: "\033[38;5;208m★\033[0m"  # Orange star
        }
        return icons.get(tier, "\033[91m?\033[0m")  # Red ? for unknown
    
    @staticmethod
    def print_tiers() -> None:
        for tier in RarityTier:
            icon = RarityTier.get_tier_icon(tier)
            print(f"{icon} {tier.value}")
   
    @staticmethod
    def print_tiers_html() -> str:
        html_parts = []
        for tier in RarityTier:
            if tier == RarityTier.COMMON:
                color = "gray"
                symbol = "●"
            elif tier == RarityTier.UNCOMMON:
                color = "green"
                symbol = "●"
            elif tier == RarityTier.RARE:
                color = "blue"
                symbol = "●"
            elif tier == RarityTier.EPIC:
                color = "purple"
                symbol = "●"
            elif tier == RarityTier.UNIQUE:
                color = "orange"
                symbol = "♦"
            elif tier == RarityTier.LEGENDARY:
                color = "darkorange"
                symbol = "★"
            else:
                color = "red"
                symbol = "?"
            html_parts.append(f'<span style="color:{color}; font-size:24px;">{symbol}</span> {tier.value}')
        html_content = "<html><body>" + "<br>".join(html_parts) + "</body></html>"
        return html_content
       