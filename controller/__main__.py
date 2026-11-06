"""Run, inspect and serve a consolidated read-only supervisor view."""
import argparse
import fcntl
import json
import resource
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

from .engine import Engine
from .store import Store


HTML = '''<!doctype html><html><head><meta charset="utf-8"><title>Outcome loop</title>
<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;background:#f4f6f8;color:#17232e}section{background:white;padding:20px;margin:16px 0;border-radius:12px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1{margin-bottom:4px}.muted{color:#596878}</style></head><body>
<h1>Outcome loop</h1><p class="muted">Workflow health, experiments, approvals and decision evidence. Refreshes every 15 seconds.</p><div id="app">Loading…</div>
<script>
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function table(rows,keys){return '<table><tr>'+keys.map(k=>'<th>'+esc(k)+'</th>').join('')+'</tr>'+rows.map(r=>'<tr>'+keys.map(k=>'<td>'+esc(r[k])+'</td>').join('')+'</tr>').join('')+'</table>'}
async function load(){try{let d=await(await fetch('/api/status')).json();document.getElementById('app').innerHTML='<section><h2>Loop health</h2><pre>'+esc(JSON.stringify({state:d.state,ingestion:d.ingestion,incidents:d.incidents,paid_operations:d.paid_operations.map(r=>({key:r.key,status:r.status}))},null,2))+'</pre></section><section><h2>KPIs · live period</h2>'+table(d.kpis.map(r=>({...r,pickup:(100*r.connected/Math.max(1,r.dials)).toFixed(1)+'%',engagement:(100*r.engaged/Math.max(1,r.connected)).toFixed(1)+'%'})),['workflow','dials','pickup','engagement','hallucinations'])+'</section><section><h2>Experiments</h2>'+table(d.experiments,['workflow','dimension','stage','started'])+'</section><section><h2>Approval queue and history</h2>'+table(d.proposals,['workflow','status','approval','created'])+'</section><section><h2>Recent decisions</h2>'+d.recent_decisions.map(r=>'<details><summary>'+esc(r.ts+' · '+r.workflow+' · '+r.kind)+'</summary><pre>'+esc(JSON.stringify(JSON.parse(r.evidence),null,2))+'</pre></details>').join('')+'</section>'}catch(e){document.getElementById('app').textContent='Unable to load controller state: '+e}}
load();setInterval(load,15000);</script></body></html>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command',choices=['run','status','why','serve'])
    ap.add_argument('--url',default='http://127.0.0.1:8700')
    ap.add_argument('--db',default='controller-data/state.sqlite')
    ap.add_argument('--workflow')
    ap.add_argument('--since',default='')
    ap.add_argument('--port',type=int,default=8800)
    args = ap.parse_args()
    if args.command=='serve':
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path not in ('/','/api/status'):
                    self.send_error(404)
                    return
                if self.path=='/':
                    data,typ = HTML.encode(),'text/html; charset=utf-8'
                else:
                    s = Store(args.db)
                    data,typ = json.dumps(s.view()).encode(),'application/json'
                    s.db.close()
                self.send_response(200)
                self.send_header('Content-Type',typ)
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(data)
        HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
        return
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
