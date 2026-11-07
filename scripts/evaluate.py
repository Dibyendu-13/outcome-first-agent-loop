#!/usr/bin/env python3
"""External evaluation harness. Controller still sees ONLY HTTP, never run files."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def run(name,scenario,port,crash,reuse_baseline=None,fault_point=None):
    rd = ROOT/'runs'/name
    report = ROOT/'reports'
    report.mkdir(exist_ok=True)
    db = ROOT/'controller-data'/(name+'.sqlite')
    if db.exists() or rd.exists():
        raise SystemExit('Use a fresh --name; evaluation never overwrites existing evidence')
    start = time.monotonic()
    baseline=Path(reuse_baseline).resolve() if reuse_baseline else rd/'baseline'
    if reuse_baseline:
        if not baseline.is_dir():raise SystemExit('Baseline directory not found')
    else:
        subprocess.run([sys.executable,'-m','sim','baseline','--scenario',scenario,'--run-dir',str(baseline)],cwd=ROOT,check=True,stdout=open(report/(name+'-baseline.log'),'w'))
    server_log = open(report/(name+'-server.log'),'w')
    server_started=time.monotonic()
    server = subprocess.Popen([sys.executable,'-m','sim','serve','--scenario',scenario,'--run-dir',str(rd/'controlled'),'--port',str(port)],cwd=ROOT,stdout=server_log,stderr=subprocess.STDOUT)
    url = f'http://127.0.0.1:{port}'
    client = httpx.Client(base_url=url,timeout=180,trust_env=False)
    recovery = []
    controller = None
    try:
        for _ in range(3600):
            if server.poll() is not None:
                raise RuntimeError('simulator failed; inspect server log')
            try:
                if client.get('/health').is_success:
                    break
            except httpx.TransportError:
                pass
            time.sleep(.25)
        else:
            raise RuntimeError('simulator startup timeout')
        startup_seconds=time.monotonic()-server_started
        log = open(report/(name+'-controller.log'),'w')
        cmd = [str(ROOT/'run.sh'),url]
        t0 = time.monotonic()
        controller_env=os.environ.copy()
        controller_env.update(CONTROLLER_DB=str(db),PYTHON=sys.executable)
        marker=ROOT/'controller-data'/(name+'.fault-marker')
        if fault_point:
            controller_env.update(CONTROLLER_FAULT_POINT=fault_point,CONTROLLER_FAULT_MARKER=str(marker))
        controller = subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=controller_env)
        if crash:
            # Kill after durable pending work appears, not at an arbitrary startup delay.
            deadline = time.monotonic()+180
            while time.monotonic()<deadline and controller.poll() is None:
                try:
                    con = sqlite3.connect(db)
                    row = con.execute('SELECT id,status FROM proposals WHERE status="pending" LIMIT 1').fetchone()
                    checkpoint = con.execute('SELECT value FROM meta WHERE key="event_id"').fetchone()
                    con.close()
                    if row:
                        recovery.append({'action':'SIGKILL','pending_proposal':row[0],'checkpoint':json.loads(checkpoint[0]),'state':client.get('/sim/state').json()})
                        controller.kill()
                        controller.wait()
                        controller = subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=controller_env)
                        break
                except sqlite3.OperationalError:
                    pass
                time.sleep(.05)
            if not recovery:
                raise RuntimeError('No pending proposal observed for crash test')
        code = controller.wait()
        if fault_point and code==-signal.SIGKILL and marker.exists():
            recovery.append({'action':'SIGKILL','point':fault_point,'state':client.get('/sim/state').json()})
            controller=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=controller_env)
            code=controller.wait()
        if code:
            raise RuntimeError(f'controller failed ({code}); inspect {name}-controller.log')
        elapsed = time.monotonic()-t0
        state = client.get('/sim/state').json()
        con = sqlite3.connect(db)
        events,ingest_seconds = con.execute('SELECT sum(events),sum(seconds) FROM chunks').fetchone()
        runtime = json.loads(con.execute('SELECT value FROM meta WHERE key="runtime"').fetchone()[0])
        duplicate_calls = con.execute('SELECT count(*)-count(DISTINCT id) FROM calls').fetchone()[0]
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        pending = con.execute('SELECT count(*) FROM proposals WHERE status IN ("prepared","pending","approved","unknown")').fetchone()[0]
        if recovery:
            proposal = con.execute('SELECT status,approval FROM proposals WHERE id=?',(recovery[0].get('pending_proposal',''),)).fetchone()
            recovery.append({'action':'restart_completed','proposal_final_status':proposal,'finished':state['finished'],'integrity':integrity,'duplicate_calls':duplicate_calls,'pending':pending})
        cycles=[json.loads(r[0]) for r in con.execute('SELECT payload FROM audit WHERE kind="decision_latency"')]
        latencies=sorted(r['seconds'] for r in cycles)
        lag_hist={}
        for row in cycles:
            for minutes,n in row.get('simulated_lag_histogram',[]):lag_hist[minutes]=lag_hist.get(minutes,0)+n
        def quantile(values,p):return values[min(len(values)-1,int((len(values)-1)*p))] if values else None
        limits={}
        for key,file in [('cpu_max','/sys/fs/cgroup/cpu.max'),('memory_max','/sys/fs/cgroup/memory.max'),('memory_peak','/sys/fs/cgroup/memory.peak')]:
            if Path(file).exists():limits[key]=Path(file).read_text().strip()
        unknown_paid=con.execute('SELECT count(*) FROM charges WHERE status="unknown"').fetchone()[0]
        con.close()
        metrics = {'scenario':scenario,'finished':state['finished'],'events':events,'ingest_seconds':ingest_seconds,'ingest_events_per_second':events/ingest_seconds,'controller_wall_seconds':elapsed,'simulator_startup_seconds':startup_seconds,
            'wall_seconds_per_simulated_day':elapsed/(state['end_minute']/1440),'database_bytes':db.stat().st_size,
            'peak_controller_rss_bytes':runtime['peak_rss_platform_units']*(1 if sys.platform=='darwin' else 1024),
            'monitoring_evaluation_interval_simulated_minutes':15,'experiment_evaluation_interval_simulated_minutes':60,
            'decision_cycle_seconds':{'count':len(latencies),'p50':quantile(latencies,.5),'p95':quantile(latencies,.95),'max':max(latencies) if latencies else None},
            'observed_call_to_evaluation_lag_simulated_minutes':sorted(lag_hist.items()),'baseline_reused':bool(reuse_baseline),'unknown_paid_operations':unknown_paid,
            'decision_lag_note':'Cycle latency includes ingestion and evaluation, excludes remote advance; simulated call lag comes from actual call timestamps. Neither includes time to permission or evidence thresholds.','integrity':integrity,'duplicate_calls':duplicate_calls,'pending_at_end':pending,'total_evaluation_seconds':time.monotonic()-start,
            'resource_limits':limits,'environment':{'platform':sys.platform,'cpu_count':os.cpu_count(),'python':sys.version}}
        (report/(name+'-metrics.json')).write_text(json.dumps(metrics,indent=2))
        if crash or fault_point:
            (report/(name+'-recovery.json')).write_text(json.dumps(recovery,indent=2))
        subprocess.run([sys.executable,'-m','sim','grade','--run',str(rd/'controlled'),'--baseline',str(baseline),'--out',str(report/(name+'.md'))],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        print(json.dumps(metrics,indent=2),flush=True)
    finally:
        if controller and controller.poll() is None:
            controller.terminate()
            controller.wait()
        server.terminate()
        server.wait()
        client.close()
        server_log.close()


if __name__=='__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--name',required=True)
    ap.add_argument('--scenario',required=True)
    ap.add_argument('--port',type=int,default=8701)
    ap.add_argument('--crash',action='store_true')
    ap.add_argument('--reuse-baseline')
    ap.add_argument('--fault-point',choices=['ingest_before_commit','proposal_after_send','apply_after_send','paid_after_send','advance_after_send'])
    a = ap.parse_args()
    run(a.name,a.scenario,a.port,a.crash,a.reuse_baseline,a.fault_point)
