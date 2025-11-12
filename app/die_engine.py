import os
import math
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime, timezone
from app.models import Proof
from app.pg_helper import PGHandler
from app.rarity_tier import RarityTier
from app.miner_class import MinerClass


"""
Diversity Incentive Engine (DIE)
----------------------------
Implements a diversity incentive mechanism to reward miners using rare AI models.
The incentive is based on the Verified Model Rarity Score (VMRS), which inversely correlates
with the frequency of model usage among verified proofs.

Model names are normalized by stripping any path/provider prefixes.

params: 
- beta: scaling factor for rarity bonus
- max_multiplier: cap on the maximum reward multiplier
- exponent: controls the steepness of rarity scaling
- active_date_range: time window for considering proofs

"""

class DiversityIncentiveEngine:
    def __init__(self, beta: float = 1.0, max_multiplier: float = 3.0):
        self.beta = beta #more reward for rarity
        self.max_multiplier = max_multiplier #cap on reward multiplier
        self.proofs: List[Proof] = []
        self.model_count: Dict[str, int] = defaultdict(int)
        self.total_verified = 0
        self.exponent = 1.2
        self.active_date_range = None
        self.bt_network = os.environ.get("BT_NETWORK", "test")
        self.bt_netuid = int(os.environ.get("BT_NETUID", 296))

    @staticmethod
    def normalize_model_name(model_name: str) -> str:
        """Normalize model name by stripping any path/provider prefixes."""
        if '/' in model_name:
            return model_name.split('/')[-1]
        return model_name

    def submit_proof(self, miner_id: str, model_name: str, base_reward: float = 1.0):
        if not miner_id or not model_name:
            return
        
        normalized_model = self.normalize_model_name(model_name)
        proof = Proof(
            miner_id=miner_id,
            model_name=normalized_model,
            base_reward=base_reward,
            timestamp=datetime.now().timestamp()
        )
        self.proofs.append(proof)
        self.model_count[normalized_model] += 1
        self.total_verified += 1
    
    def load_proofs_from_db(self, since_date: datetime):        
        pg_handler = PGHandler(os.environ.get("DATABASE_URL", ""))
        self.proofs = []
        self.model_count = defaultdict(int)
        self.total_verified = 0
        self.active_date_range = datetime.now(timezone.utc) - since_date
        records = pg_handler.select_signed_responses_formix_since(since_date, limit=500_000)
        for record in records:
            miner_id = record.get("hotkey", "")
            model_name = record.get("model", "unknown")    
            normalized_model = self.normalize_model_name(model_name)
            self.submit_proof(miner_id, normalized_model)
   
    
    def get_miner_class(self, miner_id: str) -> str:
        """
        Derive miner's class based on the entropy of their model usage history.
        """
        miner_proofs = [p for p in self.proofs if p.miner_id == miner_id]
        proof_count = len(miner_proofs)
        
        # Novice: fewer than 10 proofs
        if proof_count < 10:
            return MinerClass.NOVICE.value
        
        model_counts = defaultdict(int)
        for proof in miner_proofs:
            model_counts[proof.model_name] += 1
        
        total = proof_count
        entropy = -sum((count / total) * math.log2(count / total) for count in model_counts.values())
        max_entropy = math.log2(len(model_counts)) if model_counts else 0
        
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        if normalized_entropy > 0.7:
            return MinerClass.SORCERER.value            
        elif normalized_entropy > 0.3:
            return MinerClass.RANGER.value            
        else:
            return MinerClass.MONK.value            
   

    def get_rarity_bonus(self, model_name: str) -> float:
        """Calculate bonus based on rarity tier, not VMRS, to differentiate rewards."""
        normalized_model = self.normalize_model_name(model_name)
        tier = self.get_rarity_tier(normalized_model)
        mp = RarityTier.get_tier_multiplier(tier)
        bonus = min(mp, self.max_multiplier)
        return bonus      
    

    def get_rarity_tier(self, model_name: str) -> RarityTier:
        """
        Assign tier based on the percentile rank of the model's count among unique counts.
        All models with the same count get the same tier, scaling dynamically with the window.
        Encourages ongoing discovery by rewarding rarity relative to the current set.        
        """
        model_name = self.normalize_model_name(model_name)
        if not self.model_count or model_name not in self.model_count:
            return RarityTier.COMMON

        count = self.model_count[model_name]
        
        unique_counts = sorted(set(self.model_count.values()))
        if not unique_counts:
            return RarityTier.COMMON
        
        num_unique = len(unique_counts)
        if num_unique == 1:
            return RarityTier.LEGENDARY  # If only one count level, it's legendary
        
        # Find the rank of this count (1-based, rarest = 1)
        try:
            rank = unique_counts.index(count) + 1
        except ValueError:
            return RarityTier.COMMON
        
        # Percentile based on rank
        percentile = (rank - 1) / (num_unique - 1) if num_unique > 1 else 0
        
        if percentile <= 0.009:
            return RarityTier.UNIQUE
        elif percentile <= 0.09:
            return RarityTier.LEGENDARY
        elif percentile <= 0.25:
            return RarityTier.RARE        
        elif percentile <= 0.75:
            return RarityTier.MAGIC
        else:
            return RarityTier.COMMON
   

    def generate_rarity_report_json(self) -> dict:
        """Generate epoch report as a JSON-serializable dictionary."""
        models_list = []
        for model, count in sorted(self.model_count.items(), key=lambda x: -x[1]):
            bonus = self.get_rarity_bonus(model)
            tier = self.get_rarity_tier(model)
            rarity = f"1/{count}"
            models_list.append({
                "model": model,
                "count": count,
                "rarity": rarity,
                "tier": tier.value,
                "icon": RarityTier.get_tier_icon(tier),
                "color": RarityTier.get_html_color(tier),
                "bonus": round(bonus, 8),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        days = self.active_date_range.days if self.active_date_range else "N/A"
        dt_from = (datetime.now(timezone.utc) - self.active_date_range).isoformat() if self.active_date_range else "N/A"
        report_dict = {
            "rarity_report": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "network": self.bt_network,
                "netuid": self.bt_netuid,                
                "from": dt_from,
                "to": datetime.now(timezone.utc).isoformat(),
                "range": f"Last {days} days",
                "total_verified": self.total_verified,
                "parameters": {
                    #"beta": self.beta,
                    #"exponent": self.exponent,
                    "max_multiplier": self.max_multiplier
                },
                "models": models_list
            }
        }
        return report_dict

    def generate_miner_class_report_json(self) -> dict:
        all_miners = set(p.miner_id for p in self.proofs)
        miner_classes = []
        days = self.active_date_range.days if self.active_date_range else "N/A"
        dt_from = (datetime.now(timezone.utc) - self.active_date_range).isoformat() if self.active_date_range else "N/A"
        
        for miner_id in all_miners:
            mclass = self.get_miner_class(miner_id)
            class_color_code = MinerClass.get_color_code(MinerClass[mclass.upper()])
            class_icon = MinerClass.get_class_icon(MinerClass[mclass.upper()])

            miner_classes.append({
                "miner_hotkey": miner_id,
                "class": mclass,
                "class_icon": class_icon,
                "class_color": class_color_code,
                "proofs": len([p for p in self.proofs if p.miner_id == miner_id]),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        report_dict = {
            "miner_class_report": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "network": self.bt_network,
                "netuid": self.bt_netuid,
                "from": dt_from,
                "to": datetime.now(timezone.utc).isoformat(),
                "range": f"Last {days} days",
                "total_miners": len(all_miners),
                "miners": miner_classes
            }
        }
        return report_dict
        

    def compute_payout(self, miner_id: str) -> Tuple[float, float, str]:
        """Return (final_reward, multiplier, model_used)"""
        miner_proofs = [p for p in self.proofs if p.miner_id == miner_id]
        if not miner_proofs:
            return 0.0, 1.0, ""

        # Use latest proof (or aggregate — here: per-proof payout)
        proof = miner_proofs[-1]
        multiplier = self.get_rarity_bonus(proof.model_name)
        final = proof.base_reward * multiplier
        return final, multiplier, proof.model_name
    

    def generate_epoch_report(self) -> str:        
        max_model_len = max(len(model) for model in self.model_count.keys()) if self.model_count else 20
        max_model_len = max(max_model_len, 20)
        
        header = f"{'Tier':<10} {'Model':<{max_model_len}} {'Count':>8} {'Rarity':>10} {'Bonus':>20}"
        separator = "-" * len(header)
        
        report_lines = []
        report_lines.append(f"\n{'='*len(header)}")
        report_lines.append(f" SAMPLE EPOCH REPORT: {self.total_verified} Verified Proofs")
        #report_lines.append(f"Parameters: Beta={self.beta}, Exponent={self.exponent}, Max Multiplier={self.max_multiplier}")
        report_lines.append(f"Parameters: Max Multiplier={self.max_multiplier}")
        report_lines.append(f"{'='*len(header)}")
       
        report_lines.append(f"{'='*len(header)}")
        report_lines.append(header)
        report_lines.append(separator)

        for model, count in sorted(self.model_count.items(), key=lambda x: -x[1]):
            tier = self.get_rarity_tier(model)
            bonus = self.get_rarity_bonus(model)
            rarity_str = f"1/{count}"
            
            # Format bonus with advantage over common
            bonus_str = f"{bonus:.3f}x"
            if bonus > 1.01:
                advantage = f" (+{(bonus-1)*100:.1f}% vs common)"
            else:
                advantage = ""
            
            report_lines.append(f"{tier.value:<10} {model:<{max_model_len}} {count:>8} {rarity_str:>10} {bonus_str}{advantage:>20}")

        return "\n".join(report_lines)
    
    
    def print_epoch_report(self):
        report = self.generate_epoch_report()
        print(report)
    
    
    
if __name__ == "__main__":

# ==========================
# DEMO: Simulate an epoch
# ==========================
    print("World of Bitrecs")
    print("=================")
    print("ITEM TIERS")
    engine = DiversityIncentiveEngine(beta=1.5, max_multiplier=3.0)
    RarityTier.print_tiers()

    print("\nMINER CLASSES")
    novice_info = MinerClass.get_class_info(MinerClass.NOVICE)
    monk_info = MinerClass.get_class_info(MinerClass.MONK)
    ranger_info = MinerClass.get_class_info(MinerClass.RANGER)
    sorcerer_info = MinerClass.get_class_info(MinerClass.SORCERER)
    for info in [novice_info, monk_info, ranger_info, sorcerer_info]:
        print(f"{info['icon']} {info['name']} (Color: #{info['color_code']}) - {info['description']}")
        print(f"  Extended: {info['extended_description']}\n")

    # html_tiers = RarityTier.print_tiers_html()
    # print("\nHTML Tier Representation:")
    # print(html_tiers)

    # Simulate 1000+ miners
    miners = {
        "m1": "llama-3-8b",
        "m2": "llama-3-8b",
        "m3": "mistral-7b",
        "m4": "gemma-2b",
        "m5": "llama-3-8b",
        "m6": "mistral-7b",
        "m7": "gemma-2b",
        "m8": "llama-3-8b",
        "m9": "mistral-7b",
        "m10": "gemma-2b",
        "m11": "llama-3-8b",
        "m12": "mistral-7b",
        "m13": "gemma-2b",
        "m14": "llama-3-8b",
        "m15": "mistral-7b",
        "m16": "gemma-2b",
        "m17": "llama-3-8b",
        "m18": "mistral-7b",
        "m19": "gemma-2b"
    }

    # Popular models
    for i in range(1, 951):
        engine.submit_proof(f"m{i}", "llama-3-8b", base_reward=1.0)

    for i in range(951, 1051):
        engine.submit_proof(f"m{i}", "mistral-7b", base_reward=1.0)

    for i in range(1051, 1081):
        engine.submit_proof(f"m{i}", "gemma-2b", base_reward=1.0)

    
    engine.submit_proof("m1081", "phi-3-mini") #epic
    engine.submit_proof("m1082", "phi-3-mini")
    engine.submit_proof("m1083", "phi-3-mini")

    engine.submit_proof("m2000", "qwen-1.5b-v2") #unique  
    engine.submit_proof("m2000", "qwen-1.5b-v2")

    # Add more ultra-rare models to trigger UNIQUE tier
    engine.submit_proof("m2001", "solar-10.7b")
    engine.submit_proof("m3000", "claude-3-haiku")  # Only one!
    engine.submit_proof("m3001", "deepseek-v3")     # Only one!
    engine.submit_proof("m3002", "o1-mini")         # Only one!
    engine.submit_proof("m3003", "gemma-7b")        # Only one!

    # Add more models with varying counts to demonstrate all tiers
    # Count=4: model4
    for i in range(4000, 4004):
        engine.submit_proof(f"m{i}", "model4")
    
    # Count=5: model5
    for i in range(5000, 5005):
        engine.submit_proof(f"m{i}", "model5")
    
    # Count=6: model6
    for i in range(6000, 6006):
        engine.submit_proof(f"m{i}", "model6")
    
    # Count=7: model7
    for i in range(7000, 7007):
        engine.submit_proof(f"m{i}", "model7")
    
    # Count=8: model8
    for i in range(8000, 8008):
        engine.submit_proof(f"m{i}", "model8")
    
    # Count=9: model9
    for i in range(9000, 9009):
        engine.submit_proof(f"m{i}", "model9")
    
    # Count=10: model10
    for i in range(10000, 10010):
        engine.submit_proof(f"m{i}", "model10")

    # === Print Report ===
    engine.print_epoch_report()

    # === Show bonus for unique miners ===
    print("\n")
    print("MINERS")
    print("-" * 50)
    unique_miners = ["m2000", "m2001", "m1", "m1081", "m3000", "m3001"]
    for mid in unique_miners:
        final, mult, model = engine.compute_payout(mid)
        print(f"Miner {mid}: {model} → {mult:.3f}x → Reward = {final:.3f}")
    
    # Generate JSON report
    #json_report = engine.generate_rarity_report_json()
    #print(json.dumps(json_report, indent=2))  # Pretty-print for testing

    # miner_class_report = engine.generate_miner_class_report_json()
    # print("\nMiner Class Report:")
    # print(json.dumps(miner_class_report, indent=2))