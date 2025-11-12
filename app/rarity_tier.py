import json
from enum import Enum


class RarityTier(Enum):
    COMMON = "Common"
    MAGIC = "Magic"
    RARE = "Rare"      
    LEGENDARY = "Legendary"
    UNIQUE = "Unique"


    @staticmethod
    def get_multipliers():
        """Main Scoring Multipliers"""
        return {
            RarityTier.COMMON: 1.0,
            RarityTier.MAGIC: 1.05,
            RarityTier.RARE: 1.1,
            RarityTier.LEGENDARY: 1.9,
            RarityTier.UNIQUE: 3.0
        }


    def get_tier_multiplier(tier: 'RarityTier') -> float:
        """Return a multiplier for the tier."""
        multipliers = RarityTier.get_multipliers()              
        return multipliers.get(tier, 1.0)
    

    @staticmethod
    def get_tier_icon(tier: 'RarityTier') -> str:
        """Return a colored Unicode icon for the tier using ANSI escape codes."""
        icons = {
            RarityTier.COMMON: "\033[90m●\033[0m",          # Gray circle
            RarityTier.MAGIC: "\033[32m●\033[0m",        # Green circle
            RarityTier.RARE: "\033[35m●\033[0m",            # Purple circle                        
            RarityTier.LEGENDARY: "\033[38;5;208m♦\033[0m",  # Orange star
            RarityTier.UNIQUE: "\033[33m★\033[0m"          # Yellow diamond
        }
        return icons.get(tier, "\033[91m?\033[0m")  # Red ? for unknown
    
    
    @staticmethod
    def print_tiers() -> None:
        for tier in RarityTier:
            icon = RarityTier.get_tier_icon(tier)
            print(f"{icon} {tier.value}")

        multipliers = RarityTier.get_multipliers()
        mp = json.dumps({tier.value: mult for tier, mult in multipliers.items()}, indent=2)
        print(f"Tier Multipliers: {mp}")


    @staticmethod
    def get_html_color(tier: 'RarityTier') -> str:
        """Return the HTML color code for the tier."""
        colors = {
            RarityTier.COMMON: "gray",
            RarityTier.MAGIC: "green",
            RarityTier.RARE: "purple",                        
            RarityTier.LEGENDARY: "darkorange",
            RarityTier.UNIQUE: "gold"
        }
        return colors.get(tier, "red")  # Red for unknown
    
   
    @staticmethod
    def print_tiers_html() -> str:
        html_parts = []
        for tier in RarityTier:
            multiplier = RarityTier.get_tier_multiplier(tier)
            if tier == RarityTier.COMMON:
                color = "gray"
                symbol = "●"
            elif tier == RarityTier.MAGIC:
                color = "blue"
                symbol = "●"
            elif tier == RarityTier.RARE:
                color = "purple"
                symbol = "●"
            # elif tier == RarityTier.EPIC:
            #     color = "purple"
            #     symbol = "●"
            elif tier == RarityTier.LEGENDARY:
                color = "darkorange"                
                symbol = "♦"
            elif tier == RarityTier.UNIQUE:
                color = "gold"
                symbol = "★"                
            else:
                color = "red"
                symbol = "?"
            html_parts.append(f'<span style="color:{color}; font-size:24px;">{symbol}</span> {tier.value} ({multiplier:.2f}x)')
        html_content = "<html><body>" + "<br>".join(html_parts) + "</body></html>"
        return html_content
