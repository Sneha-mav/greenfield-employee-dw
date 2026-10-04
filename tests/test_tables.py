import pandas as pd

from app.components.tables import records_to_frame


def test_records_to_frame_accepts_manager_lists():
    frame = records_to_frame([{"review_id": 1, "performance_rating": 4}])

    assert isinstance(frame, pd.DataFrame)
    assert frame.loc[0, "review_id"] == 1


def test_records_to_frame_handles_none_as_empty_frame():
    assert records_to_frame(None).empty