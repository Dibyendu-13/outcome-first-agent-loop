"""Run, inspect and serve a consolidated read-only supervisor view."""
import argparse
import fcntl
import json
import resource
import sqlite3
from urllib.parse import urlsplit
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

from .dashboard import Dashboard
from .engine import Engine
from .store import Store


WEB = Path(__file__).with_name('web')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command',choices=['run','status','why','serve'])
    ap.add_argument('--url',default='http://127.0.0.1:8700')
    ap.add_argument('--db',default='controller-data/state.sqlite')
    ap.add_argument('--auto-db',action='store_true',help='Select/reuse state from public world progress; preserve completed worlds')
    ap.add_argument('--workflow')
    ap.add_argument('--since',default='')
    ap.add_argument('--port',type=int,default=8800)
    args = ap.parse_args()
    if args.command=='serve':
        from .observability import metrics
        if not Path(args.db).is_file():
            raise SystemExit('Controller database not found: '+args.db)
        dashboard = Dashboard(args.db)
        assets = {'/':('index.html','text/html; charset=utf-8'),
                  '/assets/dashboard.css':('dashboard.css','text/css; charset=utf-8'),
                  '/assets/dashboard.js':('dashboard.js','text/javascript; charset=utf-8'),
                  '/assets/favicon.svg':('favicon.svg','image/svg+xml')}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = urlsplit(self.path).path
                if path not in assets and path not in ('/api/status','/api/dashboard','/metrics'):
                    self.send_error(404)
                    return
                try:
                    if path in assets:
                        file,typ = assets[path]
                        data = (WEB/file).read_bytes()
                    elif path=='/metrics':
                        data,typ = metrics(args.db).encode(),'text/plain; version=0.0.4; charset=utf-8'
                    elif path=='/api/dashboard':
                        data,typ = json.dumps(dashboard.snapshot()).encode(),'application/json'
                    else:
                        store = Store(args.db,read_only=True)
                        try:
                            data,typ = json.dumps(store.view()).encode(),'application/json'
                        finally:
                            store.db.close()
                except (sqlite3.Error,OSError,ValueError):
                    self.send_response(503)
                    self.send_header('Content-Type','application/json')
                    self.send_header('Cache-Control','no-store')
                    self.end_headers()
                    self.wfile.write(b'{"error":"Controller snapshot unavailable; inspect the server log and database."}')
                    return
                self.send_response(200)
                self.send_header('Content-Type',typ)
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
                self.end_headers()
                self.wfile.write(data)
        print(f'Outcome console: http://127.0.0.1:{args.port} · {args.db}',flush=True)
        HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
        return
    if args.command=='run' and args.auto_db:
        from .lifecycle import state_path
        with httpx.Client(base_url=args.url,timeout=180,trust_env=False) as client:
            response=client.get('/sim/state');response.raise_for_status()
            args.db=state_path(args.url,response.json())
        print(json.dumps({'controller_database':args.db}),flush=True)
    s = Store(args.db)
    if args.command=='status':
        print(json.dumps(s.view(),indent=2))
        return
    if args.command=='why':
        rows = s.db.execute('SELECT ts,workflow,kind,payload FROM audit WHERE (? IS NULL OR workflow=?) AND ts>=? ORDER BY id',
                            (args.workflow,args.workflow,args.since))
        for ts,wf,kind,payload in rows:
            print(json.dumps({'ts':ts,'workflow':wf,'kind':kind,'evidence':json.loads(payload)}))
        return
    # A second process must never own the same controller state concurrently.
    lock = open(str(Path(args.db))+'.lock','a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another controller already owns this database')
    engine = Engine(args.url,s)
    t0 = time.monotonic()
    retries = 0
    try:
        while True:
            try:
                if not engine.cycle():
                    break
                retries = 0
            except (httpx.TransportError,httpx.HTTPStatusError) as e:
                retries += 1
                with s.db:
                    s.audit((s.get('state') or {}).get('ts',''),'','alert_http_failure',{'error':str(e),'attempt':retries})
                if retries>=8:
                    raise
                time.sleep(min(2**retries,30))
        with s.db:
            s.set('runtime',{'wall_seconds':time.monotonic()-t0,'peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
        print(json.dumps({'finished':True,'runtime':s.get('runtime'),'ingestion':s.view()['ingestion']}),flush=True)
    finally:
        engine.c.close()
        s.db.close()
        lock.close()


if __name__=='__main__':
    main()
