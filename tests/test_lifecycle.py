from pathlib import Path
from controller.lifecycle import state_path
from controller.store import Store


def test_default_entrypoint_resumes_same_world_and_preserves_reset_world(tmp_path):
    state={'scenario':'first','sim_minute':0,'last_event_id':100}
    first=state_path('http://localhost:8700',state,tmp_path)
    store=Store(first)
    with store.db:
        store.set('state',dict(state,sim_minute=1440))
        store.set('event_id',200)
    store.db.close()
    assert state_path('http://localhost:8700',dict(state,sim_minute=1440,last_event_id=200),tmp_path)==first
    new=state_path('http://localhost:8700',state,tmp_path)
    assert new!=first and Path(first).exists()
    assert state_path('http://localhost:8700',dict(state,scenario='second'),tmp_path)!=first
