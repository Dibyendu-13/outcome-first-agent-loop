"""Choose durable state for default run.sh invocations without overwriting prior worlds."""
import hashlib
import json
from pathlib import Path
import sqlite3
from contextlib import closing


def state_path(url,state,root='controller-data/worlds'):
    identity=hashlib.sha256(json.dumps([url.rstrip('/'),state['scenario']]).encode()).hexdigest()[:16]
    folder=Path(root)/identity;folder.mkdir(parents=True,exist_ok=True)
    files=sorted(folder.glob('state-*.sqlite'))
    if files:
        latest=files[-1]
        try:
            with closing(sqlite3.connect(latest.resolve().as_uri()+'?mode=ro',uri=True)) as db:
                meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM meta WHERE key IN ("state","event_id")')}
            previous=meta.get('state')
            if not previous or (state['sim_minute']>=previous['sim_minute'] and state['last_event_id']>=meta.get('event_id',0)):
                return str(latest)
        except sqlite3.Error:
            # An interrupted fresh schema initialization can be retried, not discarded.
            if latest.stat().st_size==0:return str(latest)
            raise
    number=int(files[-1].stem.rsplit('-',1)[1])+1 if files else 1
    return str(folder/f'state-{number:06}.sqlite')
