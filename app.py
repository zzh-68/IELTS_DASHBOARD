from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from learning import SKILLS, SOURCES, CRITERIA, label, load_data, window_stats, weaknesses, build_plan

st.set_page_config(page_title='IELTS Learning Studio', page_icon='📚', layout='wide')
st.markdown('''<style>.block-container{max-width:1400px;padding-top:2rem}div[data-testid="stMetric"]{background:#eef4fa;padding:18px;border-radius:12px}h1{letter-spacing:-1px}</style>''', unsafe_allow_html=True)
st.caption('NLP / DATA SCIENCE · EXPLAINABLE LEARNING ANALYTICS · MVP')
st.title('IELTS Personalised Learning Dashboard')
st.write('Understand your practice. Identify priorities. Build a purposeful next week.')
st.info('DEMO DATA — 20 synthetic sessions for an illustrative learner. All scores are simulated practice values, not official IELTS results or human assessments. No automated scoring or LLM is used.')
try:
    data = load_data(Path(__file__).parent / 'data/demo_sessions.csv')
except (ValueError, OSError) as exc:
    st.error(f'Unable to load data: {exc}')
    st.stop()
with st.sidebar:
    st.header('Study settings')
    learner = st.selectbox('Learner', sorted(data.learner_id.unique()))
    source = st.selectbox('Score source', SOURCES, format_func=label)
    cohort = st.selectbox('Data status', ['Demo', 'Real'])
    target = st.slider('Target per skill / criterion', 0.0, 9.0, 7.0, 0.5)
    budget = st.slider('Weekly study budget (minutes)', 35, 420, 210, 5)
    end = st.date_input('Evidence through', data.date.max().date())
    days = st.selectbox('Evidence window (days)', [30, 60, 90], index=0)
    default_start = date.today() + timedelta(days=7-date.today().weekday())
    start = st.date_input('Plan week starts', default_start)
    st.caption('Target is a planning threshold, not an overall-band calculation. Sources and Demo / Real records are analysed separately.')
filtered = data[(data.learner_id == learner) & (data.score_source == source) & (data.is_demo == (cohort == 'Demo')) & (data.date <= pd.Timestamp(end)) & (data.date >= pd.Timestamp(end-timedelta(days=days-1)))]
st.caption(f'Evidence window: {end-timedelta(days=days-1)} to {end} · {label(source)} · {cohort} · {len(filtered)} sessions')
if filtered.empty:
    st.warning('No matching records. No scores or weaknesses can be inferred. The plan below uses diagnostic activities.')
st.header('01 · Learning Overview')
cols = st.columns(4)
for skill, col in zip(SKILLS, cols):
    subset = filtered[filtered.skill.eq(skill)]
    mean, delta, n = window_stats(subset.score)
    col.metric(skill, f'{mean:.2f}' if mean is not None else 'No data', delta=f'{delta:+.2f} vs previous 3' if delta is not None else None)
    col.caption(f'Recent mean · n={n} · {len(subset)} sessions')
if not filtered.empty:
    left, right = st.columns([2, 1])
    fig = px.line(filtered, x='date', y='score', color='skill', markers=True, hover_data=['session_id', 'score_source', 'task_type'], title='Supplied scores over time')
    fig.update_yaxes(range=[0,9], title='Supplied score (0–9)')
    fig.add_hline(y=target, line_dash='dot', annotation_text='Planning target')
    left.plotly_chart(fig, width='stretch')
    counts = filtered.groupby('skill').size().reindex(SKILLS, fill_value=0).rename('Sessions').reset_index()
    right.plotly_chart(px.bar(counts, x='skill', y='Sessions', title='Practice frequency', color='skill'), width='stretch')
    st.caption(f'Total practice: {int(filtered.duration_minutes.sum())} minutes. Connecting lines describe observations; they do not predict future scores. Skill cards can combine task types; criterion analysis keeps tasks separate.')
st.header('02 · Weakness Analysis')
st.write('Writing Task 2 and Speaking criteria are analysed separately. Recent mean uses up to three observations; change requires three recent and three previous observations for the same task.')
weak = weaknesses(filtered, target)
if weak.empty:
    st.warning('No criterion observations available. Skill-level scores cannot identify criterion-level weaknesses.')
else:
    for skill in ['Writing', 'Speaking']:
        part = weak[weak.skill.eq(skill)].copy()
        if part.empty:
            continue
        left, right = st.columns([1, 1])
        chart = part.copy(); chart['Criterion'] = chart.criterion.map(label)
        fig = px.bar(chart, x='recent_mean', y='Criterion', orientation='h', color='gap', range_x=[0,9], title=f'{skill} · recent criterion means', labels={'recent_mean':'Mean supplied score','gap':'Target gap'}, hover_data=['n','task'])
        fig.add_vline(x=target, line_dash='dot')
        left.plotly_chart(fig, width='stretch')
        long = filtered[filtered.skill.eq(skill)].melt(id_vars=['date','task_type','session_id'], value_vars=CRITERIA[skill], var_name='Criterion', value_name='Score').dropna(subset=['Score'])
        long['Criterion'] = long.Criterion.map(label)
        fig = px.line(long, x='date', y='Score', color='Criterion', line_group='task_type', markers=True, title=f'{skill} · criterion history', hover_data=['session_id','task_type'])
        fig.update_yaxes(range=[0,9]); right.plotly_chart(fig, width='stretch')
    display = weak.rename(columns={'recent_mean':'Recent mean', 'n':'Recent n', 'gap':'Target gap', 'priority':'Priority', 'change':'Change'}).copy()
    display['criterion'] = display.criterion.map(label)
    st.dataframe(display, hide_index=True, width='stretch')
    st.caption('Blank change = insufficient evidence. Priority = max(0, target − recent mean) + 0.5 when change ≤ −0.5. This heuristic is unvalidated and does not establish learning gains.')
st.header('03 · Personalised Study Plan')
st.write('A transparent weekly allocation based on the selected evidence and your available time.')
plan = build_plan(filtered, target, budget, start)
for _, row in plan.iterrows():
    with st.container(border=True):
        st.markdown(f"**{row['date']} · {row['skill']} · {row['focus']}** — {row['minutes']} min")
        st.write(row['activity'])
        st.caption('Why: ' + row['reason'])
st.caption(f'Allocated {plan.minutes.sum()} of {budget} minutes. Activities are ordered by criterion priority, followed by diagnostics and Listening / Reading review; ties use skill and criterion names. This is a study aid, not a validated intervention.')
export = plan.assign(learner_id=learner, score_source=source, is_demo=cohort=='Demo', evidence_start=str(end-timedelta(days=days-1)), evidence_end=str(end), target=target)
st.download_button('Download weekly plan · CSV', export.to_csv(index=False).encode('utf-8'), 'ielts_weekly_plan.csv', 'text/csv')
with st.expander('Evidence and methodology'):
    st.dataframe(filtered, hide_index=True, width='stretch')
    st.write('Scores are read from CSV; no score is calculated from an essay or recording. Official results, human assessments and simulations are separate provenance classes. Source labels are supplied metadata and are not independently authenticated by this app. No overall IELTS band is calculated.')
    st.write('Future research: opt-in learner-reported emotion and a pluggable feedback provider. No emotion detection, external API calls, LLM or emotional inference is active.')
    st.markdown('[IELTS Writing criteria](https://ielts.org/take-a-test/preparation-resources/writing-test-resources) · [IELTS Speaking criteria](https://ielts.org/news-and-insights/demystifying-the-ielts-speaking-test)')
