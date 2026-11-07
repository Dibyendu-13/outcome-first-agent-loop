"""Atomic chunk ingestion and bounded-cardinality sufficient statistics."""
import json
import sqlite3
import time
from collections import Counter, OrderedDict
from pathlib import Path

from .faults import hit


class Store:
    def __init__(self, path, read_only=False):
        if read_only:
            self.db = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
            self.db.execute('PRAGMA query_only=ON')
            self.cache = OrderedDict()
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA cache_size=-65536')
        self.db.execute('PRAGMA temp_store=MEMORY')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,kind TEXT,events INTEGER,seconds REAL);
        CREATE TABLE IF NOT EXISTS leads(id TEXT PRIMARY KEY,workflow TEXT,person TEXT,campaign TEXT,features TEXT,concluded INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS leads_workflow ON leads(workflow,concluded);
        CREATE TABLE IF NOT EXISTS metrics(workflow TEXT,hour TEXT,version INTEGER,prompt TEXT,cohort TEXT,dim TEXT,option TEXT,
          dials INTEGER,connected INTEGER,engaged INTEGER,hallucinations INTEGER,
          PRIMARY KEY(workflow,hour,version,prompt,cohort,dim,option));
        CREATE TABLE IF NOT EXISTS calls(id INTEGER PRIMARY KEY,workflow TEXT,lead TEXT,person TEXT,ts TEXT,
          version INTEGER,cohort TEXT,prompt TEXT,voice TEXT,welcome TEXT,caller TEXT,connected INTEGER,engaged INTEGER,hallucination INTEGER);
        CREATE INDEX IF NOT EXISTS calls_lead ON calls(lead);
        CREATE INDEX IF NOT EXISTS calls_workflow_time ON calls(workflow,ts,id);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts TEXT,workflow TEXT,type TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,ts TEXT,workflow TEXT,kind TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,workflow TEXT,status TEXT,approval TEXT,body TEXT,reason TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS experiments(workflow TEXT,dim TEXT,started TEXT,stage TEXT,baseline TEXT,
          PRIMARY KEY(workflow,dim));
        CREATE TABLE IF NOT EXISTS charges(key TEXT PRIMARY KEY,status TEXT,result TEXT);
        ''')
        self.cache = OrderedDict()

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key,json.dumps(value)))

    def audit(self, ts, wf, kind, payload):
        self.db.execute('INSERT INTO audit(ts,workflow,kind,payload) VALUES (?,?,?,?)',
                        (ts,wf,kind,json.dumps(payload,sort_keys=True)))

    def ingest(self, chunk, lines):
        if self.db.execute('SELECT 1 FROM chunks WHERE id=?',(chunk['chunk'],)).fetchone():
            return 0
        t0 = time.monotonic()
        counts, n = Counter(), 0
        last = self.get('event_id',0)
        with self.db:
            for line in lines:
                if not line:
                    continue
                e = json.loads(line)
                if e['event_id'] <= last:
                    continue
                n += 1
                last = e['event_id']
                typ, wf = e['type'], e.get('workflow_id','')
                if typ == 'lead':
                    f = e['features']
                    self.db.execute('INSERT OR IGNORE INTO leads(id,workflow,person,campaign,features) VALUES (?,?,?,?,?)',
                        (e['lead_id'],wf,e['person_id'],e['campaign_id'],json.dumps(f)))
                    self.cache[e['lead_id']] = f
                    if len(self.cache)>100000:
                        self.cache.popitem(last=False)
                elif typ == 'call':
                    f = self.cache.get(e['lead_id'])
                    if f is None:
                        row = self.db.execute('SELECT features FROM leads WHERE id=?',(e['lead_id'],)).fetchone()
                        if row is None:
                            raise ValueError('call without lead: '+e['lead_id'])
                        f = json.loads(row[0])
                        self.cache[e['lead_id']]=f
                        if len(self.cache)>100000:self.cache.popitem(last=False)
                    else:
                        self.cache.move_to_end(e['lead_id'])
                    if e['engaged']:
                        self.db.execute('UPDATE leads SET concluded=1 WHERE id=?',(e['lead_id'],))
                    v = e['variant']
                    values = (1,int(e['connected']),int(e['engaged']),int((e.get('qa') or {}).get('hallucination_flag',False)))
                    self.db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (e['event_id'],wf,e['lead_id'],e.get('person_id',''),e['ts'],e['config_version'],e['cohort_id'],
                         v['prompt_version'],v['voice'],v['welcome_message'],v['caller_id'],values[1],values[2],values[3]))
                    for dim,opt in [('all','all'),('lang',f['lang'])]+[(d,v[d]) for d in ('voice','welcome_message','caller_id')]:
                        key = (wf,e['ts'][:13],e['config_version'],v['prompt_version'],e['cohort_id'],dim,opt)
                        for i,value in enumerate(values):
                            counts[key+(i,)] += value
                else:
                    self.db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)',
                        (e['event_id'],e['ts'],wf,typ,json.dumps(e)))
                    if typ in ('config_changed','approval_decided'):
                        self.audit(e['ts'],wf,typ,e)
            keys = {k[:-1] for k in counts}
            self.db.executemany('''INSERT INTO metrics VALUES (?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(workflow,hour,version,prompt,cohort,dim,option) DO UPDATE SET
              dials=dials+excluded.dials,connected=connected+excluded.connected,
              engaged=engaged+excluded.engaged,hallucinations=hallucinations+excluded.hallucinations''',
              [k+tuple(counts[k+(i,)] for i in range(4)) for k in keys])
            self.set('event_id',last)
            self.set('chunk:'+chunk['kind'],chunk['chunk'])
            hit('ingest_before_commit')
            self.db.execute('INSERT INTO chunks VALUES (?,?,?,?)',
                (chunk['chunk'],chunk['kind'],n,time.monotonic()-t0))
        return n

    def stats(self, wf, dim='all', since='', until='9999', prompt=None, version=None, cohort=None):
        until_hour=until[:13]
        if len(until)>=16 and until[14:16]!='00':
            from datetime import datetime,timedelta
            until_hour=(datetime.fromisoformat(until)+timedelta(hours=1)).isoformat()[:13]
        args = [wf,dim,since[:13],until_hour]
        where = 'workflow=? AND dim=? AND hour>=? AND hour<?'
        if cohort is not None:
            where += ' AND cohort=?'
            args.append(cohort)
        if prompt is not None:
            where += ' AND prompt=?'
            args.append(prompt)
        if version is not None:
            where += ' AND version=?'
            args.append(version)
        rows = self.db.execute(f'SELECT option,sum(dials),sum(connected),sum(engaged),sum(hallucinations) FROM metrics WHERE {where} GROUP BY option', args)
        return {r[0]:dict(zip(('dials','connected','engaged','hallucinations'),r[1:])) for r in rows}

    def view(self):
        ingestion = dict(zip(('events','seconds','chunks'),self.db.execute('SELECT coalesce(sum(events),0),coalesce(sum(seconds),0),count(*) FROM chunks').fetchone()))
        ingestion['events_per_second'] = ingestion['events']/ingestion['seconds'] if ingestion['seconds'] else 0
        ingestion['event_lag'] = max(0,(self.get('state') or {}).get('last_event_id',0)-self.get('event_id',0))
        return {
          'state':self.get('state'),
          'ingestion':ingestion,
          'incidents':{r[0].split(':',1)[1]:json.loads(r[1]) for r in self.db.execute('SELECT key,value FROM meta WHERE key LIKE "incident:%"') if json.loads(r[1])},
          'paid_operations':[dict(zip(('key','status','result'),r)) for r in self.db.execute('SELECT key,status,result FROM charges')],
          'workflows':self.get('workflows',[]),
          'experiments':[dict(zip(('workflow','dimension','started','stage','baseline'),r)) for r in self.db.execute('SELECT * FROM experiments')],
          'proposals':[dict(zip(('proposal_id','workflow','status','approval','body','reason','created'),r)) for r in self.db.execute('SELECT * FROM proposals ORDER BY created DESC')],
          'recent_decisions':[dict(zip(('ts','workflow','kind','evidence'),r)) for r in self.db.execute('SELECT ts,workflow,kind,payload FROM audit ORDER BY id DESC LIMIT 100')],
          'kpis':[dict(zip(('workflow','dials','connected','engaged','hallucinations'),r)) for r in self.db.execute('SELECT workflow,sum(dials),sum(connected),sum(engaged),sum(hallucinations) FROM metrics WHERE dim="all" AND hour>="2027-01-04" GROUP BY workflow')]
        }
