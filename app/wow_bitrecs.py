
from enum import Enum
from datetime import datetime, timedelta, timezone
from app.die_engine import DiversityIncentiveEngine
from app.rarity_tier import RarityTier
from app.miner_class import MinerClass

class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"
    SOLARIZED = "solarized"

class WorldOfBitrecs:
    @staticmethod
    def generate_html(theme: Theme = Theme.LIGHT) -> str:
        """
        Generates a basic HTML5 page for 'World of Bitrecs' with themed styling.
        Uses RarityTier and MinerClass for sample content; no external dependencies.
        """
        # Sample data (replace with actual DieEngine data if needed)
        sample_rarity = RarityTier.UNIQUE
        sample_class = MinerClass.SORCERER

        engine = DiversityIncentiveEngine()
        since_date = datetime.now(timezone.utc) - timedelta(days=14)
        engine.load_proofs_from_db(since_date)

        rarity_icon = RarityTier.get_tier_icon(sample_rarity)
        class_icon = MinerClass.get_class_icon(sample_class)
        
        # Theme CSS
        css = {
            Theme.LIGHT: """
                body { background-color: #ffffff; color: #000000; font-family: Arial, sans-serif; }
                h1 { color: #333333; }
                .rarity { color: gold; }
                .miner-class { color: blue; }
            """,
            Theme.DARK: """
                body { background-color: #121212; color: #ffffff; font-family: Arial, sans-serif; }
                h1 { color: #cccccc; }
                .rarity { color: gold; }
                .miner-class { color: lightblue; }
            """,
            Theme.SOLARIZED: """
                body { background-color: #fdf6e3; color: #586e75; font-family: Arial, sans-serif; }
                h1 { color: #dc322f; }
                .rarity { color: #b58900; }
                .miner-class { color: #268bd2; }
            """
        }
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>World of Bitrecs</title>
            <style>
                {css[theme]}
            </style>
        </head>
        <body>
            <h1>Welcome to World of Bitrecs</h1>
            <p>Explore the world of mining with dynamic incentives!</p>
            <div class="rarity">
                <h2>Sample Rarity Tier</h2>
                <p>{sample_rarity.value} {rarity_icon}</p>
            </div>
            <div class="miner-class">
                <h2>Sample Miner Class</h2>
                <p>{sample_class.value} {class_icon}</p>
            </div>
        </body>
        </html>
        """
        return html

