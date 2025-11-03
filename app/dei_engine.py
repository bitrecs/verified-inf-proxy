import os
from collections import defaultdict
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from app.models import Proof
from app.pg_helper import PGHandler
from dotenv import load_dotenv
load_dotenv()


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
    

    def load_proofs_from_db(self, since_date: datetime):        
        pg_handler = PGHandler(os.environ.get("DATABASE_URL", ""))
        self.proofs = []
        self.model_count = defaultdict(int)
        self.total_verified = 0
        records = pg_handler.select_signed_responses_formix_since(since_date, limit=10_000)
        for record in records:
            miner_id = record.get("hotkey", "")
            model_name = record.get("model", "unknown")           
            self.submit_proof(miner_id, model_name)
        

    def print_epoch_report(self):
        report = self.generate_epoch_report()
        print(report)
        

    def generate_epoch_report(self) -> str:
        # Same logic for string version
        max_model_len = max(len(model) for model in self.model_count.keys()) if self.model_count else 20
        max_model_len = max(max_model_len, 20)
        
        header = f"{'Model':<{max_model_len}} {'Count':>8} {'Rarity':>10} {'Bonus':>8}"
        separator = "-" * len(header)
        
        report_lines = []
        report_lines.append(f"\n{'='*len(header)}")
        report_lines.append(f" EPOCH REPORT: {self.total_verified} Verified Proofs")
        report_lines.append(f"{'='*len(header)}")
        report_lines.append(header)
        report_lines.append(separator)

        for model, count in sorted(self.model_count.items(), key=lambda x: -x[1]):
            vmrs = 1.0 / count
            bonus = min(1.0 + self.beta * vmrs, self.max_multiplier)
            rarity = f"1/{count}"
            report_lines.append(f"{model:<{max_model_len}} {count:>8} {rarity:>10} {bonus:>7.3f}x")

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