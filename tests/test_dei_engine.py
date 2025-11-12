from datetime import datetime, timedelta, timezone
from app.die_engine import DiversityIncentiveEngine
from app.rarity_tier import RarityTier


def test_load_defaults():
    engine = DiversityIncentiveEngine(beta=1.0, max_multiplier=3.0)
    assert engine.beta == 1.0
    assert engine.max_multiplier == 3.0
    assert engine.total_verified == 0


def test_load_from_db():
    engine = DiversityIncentiveEngine(beta=1.0, max_multiplier=3.0)
    since_date = datetime.now(timezone.utc) - timedelta(days=14)
    engine.load_proofs_from_db(since_date)
    assert engine.total_verified >= 0

    engine.print_epoch_report()


def test_rarity_tiers():
    common = RarityTier.get_tier_icon(RarityTier.COMMON)
    magic = RarityTier.get_tier_icon(RarityTier.MAGIC)
    rare = RarityTier.get_tier_icon(RarityTier.RARE)    
    unique = RarityTier.get_tier_icon(RarityTier.UNIQUE)
    legendary = RarityTier.get_tier_icon(RarityTier.LEGENDARY)
    assert common != magic != rare != unique != legendary


    

   
    



    