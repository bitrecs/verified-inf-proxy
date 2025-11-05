import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime
from app.models import Proof
from app.pg_helper import PGHandler
from dotenv import load_dotenv
load_dotenv()



class DiversityIncentiveEngine:
    def __init__(self, beta: float = 1.0, max_multiplier: float = 3.0):
        self.beta = beta #more reward for rarity
        self.max_multiplier = max_multiplier #cap on reward multiplier
        self.proofs: List[Proof] = []
        self.model_count: Dict[str, int] = defaultdict(int)
        self.total_verified = 0

    def submit_proof(self, miner_id: str, model_name: str, base_reward: float = 1.0):
        # Normalize model name: remove provider prefix (e.g., "google/" -> "gemini-2.0-flash-001")
        normalized_model = model_name.split('/')[-1] if '/' in model_name else model_name
        
        proof = Proof(
            miner_id=miner_id,
            model_name=normalized_model,  # Use normalized name
            base_reward=base_reward,
            timestamp=datetime.now().timestamp()
        )
        self.proofs.append(proof)
        self.model_count[normalized_model] += 1  # Count normalized
        self.total_verified += 1
    
    def load_proofs_from_db(self, since_date: datetime):        
        pg_handler = PGHandler(os.environ.get("DATABASE_URL", ""))
        self.proofs = []
        self.model_count = defaultdict(int)
        self.total_verified = 0
        records = pg_handler.select_signed_responses_formix_since(since_date, limit=500_000)
        for record in records:
            miner_id = record.get("hotkey", "")
            model_name = record.get("model", "unknown")           
            self.submit_proof(miner_id, model_name)

    # def get_rarity_bonus(self, model_name: str) -> float:
    #     """VMRS = 1 / count_of_model"""
    #     count = self.model_count[model_name]
    #     if count == 0:
    #         return 1.0
    #     vmrs = 1.0 / count
    #     bonus = 1.0 + self.beta * vmrs
    #     return min(bonus, self.max_multiplier)

    
    def get_rarity_bonus(self, model_name: str) -> float:
        """Exponential VMRS for stronger rarity rewards."""        
        count = self.model_count[model_name]
        if count == 0:
            return 1.0
        vmrs = 1.0 / count
        bonus = 1.0 + self.beta * (vmrs ** 2)  #adjust exponent
        return min(bonus, self.max_multiplier)

    # def get_rarity_bonus(self, model_name: str) -> float:
    #     """Logarithmic VMRS for diminishing rarity rewards."""        
    #     count = self.model_count[model_name]
    #     if count == 0:
    #         return 1.0
    #     vmrs = 1.0 / count
    #     import math
    #     bonus = 1.0 + self.beta * math.log(vmrs + 1)  # +1 to avoid log(0)
    #     return min(bonus, self.max_multiplier)
    
    # def get_rarity_bonus(self, model_name: str) -> float:
    #     """Normalized VMRS relative to the rarest model."""
    #     count = self.model_count[model_name]
    #     if count == 0 or not self.model_count:
    #         return 1.0
    #     vmrs = 1.0 / count
    #     max_vmrs = max(1.0 / c for c in self.model_count.values() if c > 0)
    #     normalized_vmrs = vmrs / max_vmrs  # 0 to 1 scale
    #     bonus = 1.0 + self.beta * normalized_vmrs
    #     return min(bonus, self.max_multiplier)
    

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
        # Same logic for string version
        max_model_len = max(len(model) for model in self.model_count.keys()) if self.model_count else 20
        max_model_len = max(max_model_len, 20)
        
        header = f"{'Model':<{max_model_len}} {'Count':>8} {'Rarity':>10} {'Bonus (simulated)':>8}"
        separator = "-" * len(header)
        
        report_lines = []
        report_lines.append(f"\n{'='*len(header)}")
        report_lines.append(f" EPOCH REPORT: {self.total_verified} Verified Proofs")
        report_lines.append(f"{'='*len(header)}")
        report_lines.append(header)
        report_lines.append(separator)

        for model, count in sorted(self.model_count.items(), key=lambda x: -x[1]):            
            bonus = self.get_rarity_bonus(model)
            rarity = f"1/{count}"
            report_lines.append(f"{model:<{max_model_len}} {count:>8} {rarity:>10} {bonus:>7.3f}x")

        return "\n".join(report_lines)
    
    
    def print_epoch_report(self):
        report = self.generate_epoch_report()
        print(report)
    
    
    def render_bonus_comparison(exponents: list, counts: list, beta: float = 1.0, max_multiplier: float = 3.0):
        """
        Renders and prints the rarity bonus for different exponents and counts.
        Useful for comparing how exponent affects incentives.
        """
        print(f"Bonus Comparison (Beta={beta}, Max Multiplier={max_multiplier})")
        print("=" * 60)
        
        for exp in exponents:
            print(f"\nExponent: {exp}")
            print("-" * 30)
            for count in counts:
                vmrs = 1.0 / count
                bonus = min(1.0 + beta * (vmrs ** exp), max_multiplier)
                print(f"  Count {count:>3}: VMRS {vmrs:>6.4f}, Bonus {bonus:>5.3f}x")



if __name__ == "__main__":

# ==========================
# DEMO: Simulate an epoch
# ==========================

    engine = DiversityIncentiveEngine(beta=1.0, max_multiplier=3.0)    

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

    # Rare models
    engine.submit_proof("m1081", "phi-3-mini")
    engine.submit_proof("m1082", "phi-3-mini")
    engine.submit_proof("m1083", "phi-3-mini")

    engine.submit_proof("m2000", "qwen-1.5b-v2")  # Only one!
    engine.submit_proof("m2000", "qwen-1.5b-v2")  # Only one!
    engine.submit_proof("m2001", "solar-10.7b")  # Only one!

    # === Print Report ===
    engine.print_epoch_report()

    # === Show bonus for unique miners ===
    print("\n")
    print("MINERS")
    print("-" * 50)
    unique_miners = ["m2000", "m2001", "m1", "m1081"]
    for mid in unique_miners:
        final, mult, model = engine.compute_payout(mid)
        print(f"Miner {mid}: {model} → {mult:.3f}x → Reward = {final:.3f}")
