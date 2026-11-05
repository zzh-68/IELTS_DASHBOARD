"""Deterministic descriptive analytics. No scoring or predictive model."""
from datetime import timedelta
import pandas as pd

SKILLS = ['Listening', 'Reading', 'Writing', 'Speaking']
SOURCES = ['simulated_practice', 'human_assessed', 'official_ielts']
CRITERIA = {
    'Writing': ['task_response', 'coherence_cohesion', 'lexical_resource', 'grammar'],
    'Speaking': ['fluency_coherence', 'lexical_resource', 'grammar', 'pronunciation'],
}
ALL_CRITERIA = sorted(set(sum(CRITERIA.values(), [])))
ACTIVITIES = {
    'task_response': 'Outline a Task 2 response; check every part of the prompt and support each main idea.',
    'coherence_cohesion': 'Rewrite one paragraph with a clear topic sentence and logical supporting sentences.',
    'lexical_resource': 'Review 10 topic collocations and use five in a fresh response; check appropriacy.',
    'grammar': 'Review recurring grammar errors, correct five sentences, then write or speak a fresh response.',
    'fluency_coherence': 'Record a two-minute answer, mark long pauses, then repeat with a short outline.',
    'pronunciation': 'Record and replay a short answer; practise word stress and intelligible sentence stress.',
}

def label(value):
    return value.replace('_', ' ').title()


def load_data(path):
    df = pd.read_csv(path)
    required = ['session_id', 'learner_id', 'date', 'skill', 'task_type', 'score_source', 'is_demo', 'score', 'duration_minutes', 'notes'] + ALL_CRITERIA
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    if df.empty:
        raise ValueError('The dataset contains no sessions.')
    if df.session_id.isna().any() or df.session_id.duplicated().any():
        raise ValueError('Session IDs must be present and unique.')
    for col in ['learner_id', 'task_type', 'skill', 'score_source']:
        if df[col].isna().any():
            raise ValueError(f'{col} must be present.')
    df['date'] = pd.to_datetime(df.date, format='%Y-%m-%d', errors='raise').dt.normalize()
    if df.date.isna().any():
        raise ValueError('Dates must be present.')
    if not df.skill.isin(SKILLS).all() or not df.score_source.isin(SOURCES).all():
        raise ValueError('Unknown skill or score source.')
    flags = df.is_demo.astype(str).str.lower()
    if not flags.isin(['true', 'false']).all():
        raise ValueError('is_demo must be true or false.')
    df['is_demo'] = flags.eq('true')
    if (df.is_demo & df.score_source.ne('simulated_practice')).any():
        raise ValueError('Demo scores must use simulated_practice.')
    for col in ['score'] + ALL_CRITERIA:
        df[col] = pd.to_numeric(df[col], errors='raise')
        values = df[col].dropna()
        if not values.between(0, 9).all() or not ((values * 2) % 1 == 0).all():
            raise ValueError(f'{col} must be a band from 0 to 9 in half-band steps.')
    if df.score.isna().any():
        raise ValueError('Each session needs an explicitly supplied score.')
    df['duration_minutes'] = pd.to_numeric(df.duration_minutes, errors='raise')
    if df.duration_minutes.isna().any() or not df.duration_minutes.between(1, 1440).all():
        raise ValueError('Duration must be between 1 and 1440 minutes.')
    for _, row in df.iterrows():
        allowed = CRITERIA.get(row.skill, [])
        if any(pd.notna(row[c]) for c in ALL_CRITERIA if c not in allowed):
            raise ValueError('Criterion does not match the session skill.')
        if row.skill == 'Writing' and row.task_type != 'Task 2':
            raise ValueError('This MVP supports Writing Task 2 only.')
    return df.sort_values(['date', 'session_id']).reset_index(drop=True)


def window_stats(values):
    values = values.dropna()
    recent = values.tail(3)
    previous = values.iloc[max(0, len(values)-6):max(0, len(values)-3)]
    delta = float(recent.mean() - previous.mean()) if len(recent) == 3 and len(previous) == 3 else None
    return float(recent.mean()) if len(recent) else None, delta, len(recent)


def weaknesses(df, target):
    rows = []
    for skill, criteria in CRITERIA.items():
        for task, group in df[df.skill.eq(skill)].groupby('task_type', sort=True):
            for criterion in criteria:
                mean, delta, n = window_stats(group[criterion])
                if mean is None:
                    continue
                gap = max(0., target - mean)
                declining = delta is not None and delta <= -0.5
                rows.append(dict(skill=skill, task=task, criterion=criterion, recent_mean=mean,
                                 change=delta, n=n, gap=gap,
                                 priority=gap + (0.5 if declining else 0.)))
    return pd.DataFrame(rows)


def build_plan(df, target, minutes, start):
    """Caller supplies one learner/source/demo cohort; budget is allocated in 5-minute units."""
    if df.learner_id.nunique() > 1 or df.score_source.nunique() > 1 or df.is_demo.nunique() > 1:
        raise ValueError('Choose one learner, source and demo status before planning.')
    candidates = []
    weak = weaknesses(df, target)
    if not weak.empty:
        for row in weak.sort_values(['priority', 'skill', 'criterion'], ascending=[False, True, True]).to_dict('records'):
            if row['priority'] <= 0:
                continue
            trend = 'trend unavailable (six observations required)' if pd.isna(row['change']) else f"change {row['change']:+.2f} versus previous three"
            candidates.append((row['skill'], label(row['criterion']), ACTIVITIES[row['criterion']],
                               f"Recent mean {row['recent_mean']:.2f}, n={row['n']}; target gap {row['gap']:.2f}; {trend}. Priority {row['priority']:.2f}."))
    for skill in SKILLS:
        subset = df[df.skill.eq(skill)]
        if subset.empty:
            candidates.append((skill, 'Diagnostic', f'Complete one {skill.lower()} diagnostic and record its source.', 'No comparable sessions in the selected evidence window.'))
        elif skill not in CRITERIA:
            mean, delta, n = window_stats(subset.score)
            candidates.append((skill, 'Targeted review', f'Complete a timed {skill.lower()} set and review errors by question type.', f'Recent supplied score mean {mean:.2f}, n={n}; target gap {max(0, target-mean):.2f}. No question-level diagnosis available.'))
        elif not subset[CRITERIA[skill]].notna().any().any():
            candidates.append((skill, 'Criterion assessment', 'Request criterion-level feedback from a teacher before choosing a specific weakness.', 'No criterion scores supplied; skill score cannot identify individual weaknesses.'))
    if not candidates:
        candidates = [('Writing / Speaking', 'Maintenance', 'Complete a fresh response and request feedback using the rubric.', 'No observed criterion below target or declining by 0.5; maintain practice. This does not establish exam readiness.')]
    units = int(minutes) // 5
    candidates = candidates[:min(7, units)]
    base, extra = divmod(units, len(candidates))
    return pd.DataFrame([{'date': (pd.Timestamp(start).date() + timedelta(days=i)).isoformat(),
                          'skill': s, 'focus': f, 'minutes': 5*(base + (i < extra)),
                          'activity': a, 'reason': r} for i, (s, f, a, r) in enumerate(candidates)])
