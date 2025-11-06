from enum import Enum

class RarityTier(Enum):
    COMMON     = ("Common",     "§7")   # gray
    UNCOMMON   = ("Uncommon",   "§a")   # green
    RARE       = ("Rare",       "§9")   # blue
    EPIC       = ("Epic",       "§5")   # purple
    UNIQUE     = ("Unique",     "§6")   # orange

    def __init__(self, name: str, color_code: str):
        self.display_name = name
        self.color = color_code