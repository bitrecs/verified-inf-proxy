from app.utils import iso_to_relative_time


def test_can_parse_iso_time():
    iso_ts = "2024-06-15T12:00:00Z"
    relative_time = iso_to_relative_time(iso_ts)
    assert relative_time.endswith("ago") or relative_time == "in the future"
    