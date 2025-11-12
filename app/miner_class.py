from enum import Enum


CLASS_COLOR_MAPPING = {
    "Novice": "C0C0C0",    # Grey plain Male for Novice
    "Monk": "996633",      # Dark Brown Male Diablo2 Paladin 
    "Ranger": "006600",    # Dark Green Female Diablo2 Amazon
    "Sorcerer": "0000FF"   # Blue Female Diablo2 Sorcerer
}


MINER_CLASS_DESCRIPTIONS = {
    "Novice": "Novice with <10 proofs",
    "Monk": "Focused miners using few models for consistency.",
    "Ranger": "Balanced miners with moderate model variety.",
    "Sorcerer": "Diverse miners exploring many models."
}


MINER_CLASS_DESCRIPTIONS_EXTENDED = {
    "Novice": "New miners with fewer than 10 proofs, representing new adventurers.",
    "Monk": "Low-diversity miners (entropy ≤ 0.3) who stick mostly to one or few models, rewarding deep focus and consistency.",
    "Ranger": "Balanced miners (0.3 < entropy ≤ 0.7) with moderate diversity, using a mix of models flexibly without extreme focus or spread.",
    "Sorcerer": "High-diversity miners (entropy > 0.7) who use many different models evenly, encouraging broad exploration and discovery of rare models."
}



class MinerClass(Enum):
    NOVICE = "Novice"
    MONK = "Monk"
    RANGER = "Ranger"
    SORCERER = "Sorcerer"

    @staticmethod
    def classify_miner(entropy: float, total_proofs: int):
        if total_proofs < 10:
            return MinerClass.NOVICE
        elif entropy > 0.7:
            return MinerClass.SORCERER
        elif entropy > 0.3:
            return MinerClass.RANGER
        else:
            return MinerClass.MONK
        
    def get_color_code(miner_class: 'MinerClass') -> str:
        """Return the HTML color code for the miner class."""
        return CLASS_COLOR_MAPPING.get(miner_class.value, "000000")  # Default to black if unknown
    
    @staticmethod
    def get_class_icon(miner_class: 'MinerClass') -> str:
        """Return a colored Unicode icon for the miner class using ANSI escape codes."""
        icons = {
            MinerClass.NOVICE: "\033[90m♂\033[0m",     # Grey Male
            MinerClass.MONK: "\033[33m♂\033[0m",       # Dark Brown Male
            MinerClass.RANGER: "\033[32m♀\033[0m",     # Dark Green Female
            MinerClass.SORCERER: "\033[34m♀\033[0m"    # Blue Female
        }
        return icons.get(miner_class, "\033[91m?\033[0m")  # Red ? for unknown  
            
       
 

