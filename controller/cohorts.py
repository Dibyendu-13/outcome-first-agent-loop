"""One ordered cohort definition shared by learning, detection and presentation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Cohort:
    id: str
    where: dict

    def matches(self, features):
        return all(features.get(key) in values for key,values in self.where.items())

    def config(self):
        return {'id':self.id,'where':self.where}


def registry(config):
    return [Cohort(c['id'],c['where']) for c in config.get('cohorts',[])]+[Cohort('default',{})]


def classify(config, features):
    return next(c.id for c in registry(config) if c.matches(features))


def definitions(store, workflow, config, minimum_people=400):
    """Keep client definitions; otherwise select disjoint, sufficiently populated language groups."""
    if config.get('cohorts'):
        return config['cohorts']
    rows = store.db.execute('SELECT json_extract(features,"$.lang"),count(DISTINCT person) FROM leads WHERE workflow=? GROUP BY 1',(workflow['workflow_id'],))
    eligible = {lang:n for lang,n in rows if n>=minimum_people}
    return [Cohort('lang_'+lang,{'lang':[lang]}).config() for lang in sorted(workflow.get('languages',[])) if lang in eligible][:19] if len(eligible)>1 else []
