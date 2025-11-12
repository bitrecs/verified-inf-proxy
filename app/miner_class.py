from enum import Enum

CLASS_COLOR_MAPPING = {
    "Novice": "C0C0C0", # Silver    
    "Monk": "D6133A",   # Red
    "Ranger": "00E070", # Green    
    "Sorcerer": "0066FF" # Blue   
}

CLASS_ICON_MAPPING = {
    "Novice": "\u001B[97m🔰\u001B[0m",
    "Monk": "\u001B[91m🤛\u001B[0m",
    "Ranger": "\u001B[92m🏹\u001B[0m",
    "Sorcerer": "\u001B[94m⚡️\u001B[0m"
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
        
    @staticmethod
    def get_color_code(miner_class: 'MinerClass') -> str:
        """Return the HTML color code for the miner class."""
        return CLASS_COLOR_MAPPING.get(miner_class.value, "000000")  # Default to black if unknown
    
    @staticmethod
    def get_class_icon(miner_class: 'MinerClass') -> str:
        """Return a colored Unicode icon for the miner class using ANSI escape codes."""
        return CLASS_ICON_MAPPING.get(miner_class.value, "\u001B[90m❓\u001B[0m")
    
    @staticmethod
    def get_class_description(miner_class: 'MinerClass') -> str:
        """Return a short description for the miner class."""
        return MINER_CLASS_DESCRIPTIONS.get(miner_class.value, "Unknown class")
    
    @staticmethod
    def get_class_description_extended(miner_class: 'MinerClass') -> str:
        """Return an extended description for the miner class."""
        return MINER_CLASS_DESCRIPTIONS_EXTENDED.get(miner_class.value, "No description available.")
    
    @staticmethod
    def get_class_info(miner_class: 'MinerClass') -> dict:
        """Return a dictionary with all info about the miner class."""
        return {
            "name": miner_class.value,
            "color_code": MinerClass.get_color_code(miner_class),
            "icon": MinerClass.get_class_icon(miner_class),
            "description": MinerClass.get_class_description(miner_class),
            "extended_description": MinerClass.get_class_description_extended(miner_class)
        }


       
            
       
 

