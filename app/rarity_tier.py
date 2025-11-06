from enum import Enum

class RarityTier(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    UNIQUE = "Unique"


    @staticmethod
    def get_tier_icon(tier: 'RarityTier') -> str:
        """Return a colored Unicode icon for the tier using ANSI escape codes."""
        icons = {
            RarityTier.COMMON: "\033[90m●\033[0m",    # Gray circle
            RarityTier.UNCOMMON: "\033[32m●\033[0m",  # Green circle
            RarityTier.RARE: "\033[34m●\033[0m",      # Blue circle
            RarityTier.EPIC: "\033[35m●\033[0m",      # Purple circle
            RarityTier.UNIQUE: "\033[38;5;208m★\033[0m",    # Orange star (unique symbol)
        }
        return icons.get(tier, "\033[91m?\033[0m")  # Red ? for unknown