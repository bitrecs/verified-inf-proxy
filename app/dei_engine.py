import math
from collections import defaultdict
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Proof:
    miner_id: str
    model_name: str
    base_reward: float
    timestamp: float

class DiversityIncentiveEngine:
    def __init__(self, beta: float = 1.0, max_multiplier: float = 3.0):
        self.beta = beta
        self.max_multiplier = max_multiplier
        self.proofs: List[Proof] = []
        self.model_count: Dict[str, int] = defaultdict(int)
        self.total_verified = 0

    def submit_proof(self, miner_id: str, model_name: str, base_reward: float = 1.0):        
        proof = Proof(
            miner_id=miner_id,
            model_name=model_name,
            base_reward=base_reward,
            timestamp=datetime.now().timestamp()
        )
        self.proofs.append(proof)
        self.model_count[model_name] += 1
        self.total_verified += 1

    def get_rarity_bonus(self, model_name: str) -> float:
        """VMRS = 1 / count_of_model"""
        count = self.model_count[model_name]
        if count == 0:
            return 1.0
        vmrs = 1.0 / count
        bonus = 1.0 + self.beta * vmrs
        return min(bonus, self.max_multiplier)

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

    def print_epoch_report(self):
        print(f"\n{'='*60}")
        print(f" EPOCH REPORT: {self.total_verified} Verified Proofs")
        print(f"{'='*60}")
        print(f"{'Model':<20} {'Count':>8} {'Rarity':>10} {'Bonus':>8}")
        print("-" * 60)

        for model, count in sorted(self.model_count.items(), key=lambda x: -x[1]):
            vmrs = 1.0 / count
            bonus = min(1.0 + self.beta * vmrs, self.max_multiplier)
            rarity = f"1/{count}"
            print(f"{model:<20} {count:>8} {rarity:>10} {bonus:>7.3f}x")

        print(f"\nTop unique models get up to {self.max_multiplier:.1f}x reward!\n")

    def generate_epoch_report(self) -> str:
        report_lines = []
        report_lines.append(f"\n{'='*60}")
        report_lines.append(f" EPOCH REPORT: {self.total_verified} Verified Proofs")
        report_lines.append(f"{'='*60}")
        report_lines.append(f"{'Model':<20} {'Count':>8} {'Rarity':>10} {'Bonus':>8}")
        report_lines.append("-" * 60)

        for model, count in sorted(self.model_count.items(), key=lambda x: -x[1]):
            vmrs = 1.0 / count
            bonus = min(1.0 + self.beta * vmrs, self.max_multiplier)
            rarity = f"1/{count}"
            report_lines.append(f"{model:<20} {count:>8} {rarity:>10} {bonus:>7.3f}x")

        #report_lines.append(f"\nTop unique models get up to {self.max_multiplier:.1f}x reward!\n")
        return "\n".join(report_lines)


# ==========================
# DEMO: Simulate an epoch
# ==========================
if __name__ == "__main__":
    engine = DiversityIncentiveEngine(beta=1.0, max_multiplier=3.0)

    # Simulate 1000+ miners
    miners = {
        "m1": "llama-3-8b",
        "m2": "llama-3-8b",
        # ... many using popular models
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
    engine.submit_proof("m2001", "solar-10.7b")  # Only one!

    # === Print Report ===
    engine.print_epoch_report()

    # === Show payouts for unique miners ===
    print("INDIVIDUAL PAYOUTS")
    print("-" * 50)
    unique_miners = ["m2000", "m2001", "m1", "m1081"]
    for mid in unique_miners:
        final, mult, model = engine.compute_payout(mid)
        print(f"Miner {mid}: {model} → {mult:.3f}x → Reward = {final:.3f}")