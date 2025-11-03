from datetime import datetime, timedelta, timezone
from app.dei_engine import DiversityIncentiveEngine


def test_load_defaults():
    engine = DiversityIncentiveEngine(beta=1.0, max_multiplier=3.0)
    assert engine.beta == 1.0
    assert engine.max_multiplier == 3.0
    assert engine.total_verified == 0


def test_load_from_db():
    engine = DiversityIncentiveEngine(beta=1.0, max_multiplier=3.0)
    since_date = datetime.now(timezone.utc) - timedelta(days=7)
    engine.load_proofs_from_db(since_date)
    assert engine.total_verified >= 0

    engine.print_epoch_report()


   
    



    