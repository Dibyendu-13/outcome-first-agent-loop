"""Clarify a legacy evaluation field without changing measured benchmark values."""
import json
from pathlib import Path

for path in Path('reports').glob('*-metrics.json'):
    data = json.loads(path.read_text())
    if 'decision_lag_simulated_minutes_upper_bound' in data:
        data['monitoring_evaluation_interval_simulated_minutes'] = data.pop('decision_lag_simulated_minutes_upper_bound')
        data['experiment_evaluation_interval_simulated_minutes'] = 1440
        data['decision_lag_note'] = 'Evaluation intervals exclude startup ingestion, sample-size and governance delays; actual wall-clock lag not separately measured'
        path.write_text(json.dumps(data,indent=2)+'\n')
