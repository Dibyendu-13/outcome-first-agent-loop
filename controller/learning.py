"""Durable cohort experiments, independent-person evidence and governed decay rollback."""
import copy
import json
from datetime import datetime,timedelta

from .cohorts import definitions,registry
from .statistics import MILESTONES,comparison_alpha,fisher_greater,noninferiority,binomial_bounds


def plus(ts,minutes):
    return (datetime.fromisoformat(ts)+timedelta(minutes=minutes)).isoformat()


class Learner:
    def __init__(self, engine):
        self.e,self.s=engine,engine.s

    def units(self,wid,trial,cur):
        """Only actual epoch-version calls; first dial/first connection per person.

        Person de-duplication spans returning enrollments. Sample prefixes are
        fixed by event ID and are never selected by outcome. Campaign-locked calls
        from older versions are excluded rather than credited to an unrun arm.
        """
        dim=trial['dimension']
        column={'voice':'voice','welcome_message':'welcome','caller_id':'caller'}[dim]
        seen={'pickup':set(),'engagement':set()}
        output={c.id:{'pickup':{},'engagement':{}} for c in registry(cur['config'])}
        rows=self.s.db.execute(f'''SELECT c.person,c.cohort,c.{column},c.connected,c.engaged,c.id,c.ts
          FROM calls c WHERE c.workflow=? AND c.ts>=? AND c.version=? AND c.prompt=? ORDER BY c.id''',
          (wid,trial['started'],trial['version'],cur['config']['prompt_version']))
        for person,cohort,arm,connected,engaged,event_id,ts in rows:
            if cohort not in output:continue
            for metric,eligible,value in [('pickup',True,connected),('engagement',connected,engaged)]:
                if eligible and person not in seen[metric]:
                    seen[metric].add(person)
                    values=output[cohort][metric].setdefault(arm,[])
                    # Enough for every declared look; retain bounded memory for large runs.
                    if len(values)<MILESTONES[-1]:values.append(value)
        return output

    def step(self,w,cur,state):
        wid,ts=w['workflow_id'],state['ts']
        trial=self.s.get('learning:'+wid)
        if trial and trial['stage'] in ('rolled_back','abandoned'):
            with self.s.db:
                done=self.s.get('learning_completed:'+wid,[])
                self.s.set('learning_completed:'+wid,list(dict.fromkeys(done+[trial['dimension']])))
                self.s.set('learning:'+wid,None)
            trial=None
        if trial and trial['version']!=cur['version']:
            with self.s.db:
                self.s.audit(ts,wid,'experiment_suspended',{'dimension':trial['dimension'],'expected_version':trial['version'],'actual_version':cur['version'],'reason':'configuration changed; do not mix treatment epochs'})
                self.s.set('learning:'+wid,None)
            trial=None
        if not trial:
            if int(ts[11:13])!=11 or ts[14:16]!='00':return False
            dims=['caller_id'] if w['objective']['primary']=='pickup_rate' else ['voice','welcome_message','caller_id']
            completed=self.s.get('learning_completed:'+wid,[])
            dim=next((d for d in dims if d not in self.s.get('protected:'+wid,[]) and d not in completed and 1<len(w['options'][d])<=10),None)
            if not dim:return False
            cfg=copy.deepcopy(cur['config'])
            cfg['cohorts']=definitions(self.s,w,cfg)
            cohorts=registry(cfg)
            controls={}
            for c in cohorts:
                cfg['allocations'].setdefault(c.id,{})
                old=cfg['allocations'][c.id].get(dim,cfg['allocations']['default'][dim])
                controls[c.id]=max(sorted(old),key=old.get)
                cfg['allocations'][c.id][dim]={opt:.5*old.get(opt,0)+.5/len(w['options'][dim]) for opt in w['options'][dim]}
            epoch=self.s.get('learning_epoch:'+wid,0)+1
            trial=dict(epoch=epoch,dimension=dim,cohorts=[c.config() for c in cohorts],controls=controls,
                options=w['options'][dim],baseline=copy.deepcopy(cur['config']),stage='exploring',tested={},promoted={},created=ts)
            return self.e.propose(w,cur,cfg,ts,'Measure '+dim+' alternatives in shared cohorts',
                {'estimated_lift':0,'uncertainty':'50% incumbent mixture plus 50% exploration; no benefit claimed','cohorts':trial['cohorts'],
                 'statistical_unit':'first observation per person per KPI per epoch','milestones':list(MILESTONES)},
                {'dimension':dim,'stage':'exploring','baseline':cur['config']['allocations']['default'][dim],'learning':trial})
        if ts[14:16]!='00':return False
        analysis_trial=trial
        monitor_window=1
        if trial['stage']=='promoted':
            age=(datetime.fromisoformat(ts)-datetime.fromisoformat(trial['started'])).total_seconds()/60
            window_minutes=trial.get("monitor_minutes",180)
            local_window=max(1,int(age//window_minutes)+1)
            monitor_window=trial.get('window_offset',0)+local_window
            if monitor_window!=trial.get('monitor_window'):
                trial['monitor_window']=monitor_window;trial['tested']={};trial.pop('rejected_looks',None)
                with self.s.db:self.s.set('learning:'+wid,trial)
            analysis_trial=copy.deepcopy(trial)
            analysis_trial['started']=plus(trial['started'],window_minutes*(local_window-1))
        data=self.units(wid,analysis_trial,cur)
        dim=trial['dimension'];primary='pickup' if w['objective']['primary']=='pickup_rate' else 'engagement'
        other='engagement' if primary=='pickup' else 'pickup'
        margin=w['objective']['guardrail'].get(other+'_rate_max_drop',.02)
        previous_pending=trial.get('pending',{})
        cfg=copy.deepcopy(previous_pending.get('config',cur['config']));changes=list(previous_pending.get('changes',[]));evidence=list(previous_pending.get('evidence',[]))
        # A guardrail breach requires rollback even if the primary KPI is still winning.
        if trial['stage']=='promoted':
            for cohort,streams in data.items():
                incumbent=trial['promoted'].get(cohort);control=trial['controls'][cohort]
                if not incumbent or incumbent==control:continue
                old=streams[other].get(control,[]);new=streams[other].get(incumbent,[])
                alpha_h=.5*comparison_alpha(trial['epoch'],len(data),len(trial['options'])-1,'decay')/(monitor_window*(monitor_window+1))
                for n in MILESTONES:
                    if min(len(old),len(new))<n:continue
                    key=f'{cohort}:{incumbent}:guardrail-decay:{n}'
                    if key in trial['tested']:continue
                    lo,_=binomial_bounds(sum(old[:n]),n,alpha_h/2)
                    _,hi=binomial_bounds(sum(new[:n]),n,alpha_h/2)
                    trial['tested'][key]={'lower_guardrail_recovery':lo-hi,'alpha':alpha_h,'n':n}
                    if lo-hi<=margin:continue
                    pa=streams[primary].get(control,[]);pb=streams[primary].get(incumbent,[]);pn=min(len(pa),len(pb))
                    row=dict(cohort=cohort,candidate=control,control=incumbent,n=pn,successes=[sum(pa[:pn]),sum(pb[:pn])],
                        guardrail_breach=True,guardrail_n=n,guardrail_lower_recovery=lo-hi,margin=margin,alpha=alpha_h,
                        dimension=dim,epoch=trial['epoch'],statistical_unit='independent person',
                        arm_observations={arm:{'n':len(v),'successes':sum(v)} for arm,v in streams[primary].items()})
                    cfg['allocations'].setdefault(cohort,{})[dim]=trial['baseline']['allocations'].get(cohort,{}).get(dim,trial['baseline']['allocations']['default'][dim])
                    changes=[c for c in changes if c[0]!=cohort];evidence=[r for r in evidence if r['cohort']!=cohort]
                    changes.append((cohort,control,'rollback'));evidence.append(row)
                    with self.s.db:self.s.audit(ts,wid,'cohort_guardrail_breach',row)
                    break
        for cohort,streams in data.items():
            if any(r['cohort']==cohort and r.get('guardrail_breach') for r in evidence):continue
            control=trial['controls'][cohort]
            if trial['stage']=='promoted':
                incumbent=trial['promoted'].get(cohort)
                if not incumbent:continue
                candidates=[control] if incumbent!=control else []
                comparison_control=incumbent
            else:
                candidates=[a for a in trial['options'] if a!=control]
                comparison_control=control
            for candidate in candidates:
                a=streams[primary].get(candidate,[]);b=streams[primary].get(comparison_control,[])
                purpose='decay' if trial['stage']=='promoted' else 'promotion'
                alpha=comparison_alpha(trial['epoch'],len(data),len(trial['options'])-1,purpose)
                if purpose=='decay':alpha/=2*monitor_window*(monitor_window+1)
                latest=None
                for n in MILESTONES:
                    if min(len(a),len(b))<n:continue
                    key=f'{cohort}:{candidate}:{purpose}:{n}'
                    if key not in trial['tested']:
                        p=fisher_greater(sum(a[:n]),n,sum(b[:n]),n)
                        row=dict(cohort=cohort,candidate=candidate,control=comparison_control,n=n,successes=[sum(a[:n]),sum(b[:n])],p_value=p,alpha=alpha,statistical_unit='independent person',dimension=dim,epoch=trial['epoch'])
                        trial['tested'][key]=row
                        with self.s.db:self.s.audit(ts,wid,'experiment_look',dict(**row,result='primary improvement' if p<=alpha else 'no promotion'))
                    latest=trial['tested'][key]
                latest_key=f'{cohort}:{candidate}:{purpose}:{latest["n"]}' if latest else ''
                if not latest or latest['p_value']>alpha or latest_key in trial.get('rejected_looks',[]):continue
                row=copy.deepcopy(latest)
                ga=streams[other].get(candidate,[]);gb=streams[other].get(comparison_control,[])
                gn=next((k for k in reversed(MILESTONES) if min(len(ga),len(gb))>=k),None)
                if not gn:continue
                alpha_g=.5*comparison_alpha(trial['epoch'],len(data),len(trial['options'])-1,'guardrail')
                if purpose=='decay':alpha_g/=monitor_window*(monitor_window+1)
                safe,lower=noninferiority(sum(ga[:gn]),gn,sum(gb[:gn]),gn,margin,alpha_g)
                row.update(guardrail=dict(metric=other,n=gn,lower_difference=lower,margin=margin,alpha=alpha_g,passed=safe),
                    arm_observations={arm:{'n':len(values),'successes':sum(values)} for arm,values in streams[primary].items()})
                if not safe:
                    guard_key=f'guardrail:{cohort}:{candidate}:{gn}'
                    if guard_key not in trial['tested']:
                        trial['tested'][guard_key]=row
                        with self.s.db:self.s.audit(ts,wid,'guardrail_blocked',row)
                    continue
                effect=(row['successes'][0]-row['successes'][1])/row['n']
                prior=next((r for r in evidence if r['cohort']==cohort),None)
                if prior and effect<=(prior['successes'][0]-prior['successes'][1])/prior['n']:continue
                changes=[c for c in changes if c[0]!=cohort]
                evidence=[r for r in evidence if r['cohort']!=cohort]
                if trial['stage']=='promoted':
                    old=trial['baseline']['allocations'].get(cohort,{}).get(dim,trial['baseline']['allocations']['default'][dim])
                    cfg['allocations'].setdefault(cohort,{})[dim]=old
                    changes.append((cohort,control,'rollback'))
                else:
                    allocation={control:.2,candidate:.8}
                    cfg['allocations'].setdefault(cohort,{})[dim]=allocation
                    changes.append((cohort,candidate,'promote'))
                evidence.append(row)
        with self.s.db:
            self.s.set('learning_evidence:'+wid,{'ts':ts,'epoch':trial['epoch'],'version':trial['version'],'since':analysis_trial['started'],'monitor_window':monitor_window,'cohorts':{
                cohort:{metric:{arm:{'n':len(values),'successes':sum(values)} for arm,values in arms.items()} for metric,arms in streams.items()}
                for cohort,streams in data.items()}})
        # Persist consumed looks even if permission is unavailable, retaining a decision for later submission.
        pending=trial.get('pending')
        if changes:
            if trial['stage']=='exploring':
                chosen={c for c,_,_ in changes}
                for cohort in data:
                    if cohort not in chosen:
                        cfg['allocations'].setdefault(cohort,{})[dim]=trial['baseline']['allocations'].get(cohort,{}).get(dim,trial['baseline']['allocations']['default'][dim])
            pending=dict(config=cfg,changes=changes,evidence=evidence)
            trial['pending']=pending
        with self.s.db:self.s.set('learning:'+wid,trial)
        if not pending:return False
        # Rebase only onto the exact epoch version; step() invalidates on any external edit.
        next_trial=copy.deepcopy(trial);next_trial.pop('pending',None);next_trial['tested']={}
        rollback=any(c[2]=='rollback' for c in pending['changes'])
        if rollback:
            rolled={cohort for cohort,_,action in pending['changes'] if action=='rollback'}
            next_trial['rolled_back_cohorts']=sorted(set(trial.get('rolled_back_cohorts',[]))|rolled)
            next_trial['promoted']={c:a for c,a in trial['promoted'].items() if c not in rolled}
            # Other cohorts still have live winners. Preserve their remaining alpha budget across the new config version.
            next_trial['stage']='promoted' if next_trial['promoted'] else 'rolled_back'
            next_trial['window_offset']=monitor_window
        else:
            next_trial['stage']='promoted'
            next_trial['promoted'].update({c:a for c,a,_ in pending['changes']})
            elapsed = (datetime.fromisoformat(ts)-datetime.fromisoformat(trial['started'])).total_seconds()/60
            # Forecast sentinel support using all observed eligible exposure, including quiet hours.
            support = [
                sum(len(arm) for arm in data[cohort][metric].values())
                for cohort in next_trial['promoted']
                for metric in ('pickup','engagement')
            ]
            minutes = MILESTONES[0]*max(60,elapsed)/(.2*max(1,min(support)))
            next_trial['monitor_minutes'] = int(min(1440,max(180,60*((minutes+59)//60))))

        lift=max((r['successes'][0]-r['successes'][1])/r['n'] if r['n'] else 0 for r in pending['evidence'])
        return self.e.propose(w,cur,pending['config'],ts,
            ('Rollback after cohort guardrail breach: ' if any(r.get('guardrail_breach') for r in pending['evidence']) else 'Rollback after measured winner decay: ' if rollback else 'Promote measured cohort improvement: ')+dim,
            {'estimated_lift':max(0,lift),'rollback_requested':rollback,'cohort_comparisons':pending['evidence'],'method':'fixed independent-person milestones; exact Fisher with alpha spending; exact guardrail bounds'},
            {'dimension':dim,'stage':next_trial['stage'],'baseline':trial['baseline']['allocations']['default'][dim],'learning':next_trial})
