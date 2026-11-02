# LearnBridge

**A lightweight web platform for tracking training impact, from needs assessment to results at work.**

Live demo: **https://joey6goodman.github.io/learnbridge/**
Training team view: **https://joey6goodman.github.io/learnbridge/#admin**
Sample evaluation report: [report.md](report.md)

---

## Why LearnBridge

Most training platforms ask one question at the end of a course: *did you like it?* For organisations that train public officials, that is not the question funders care about. They want to know whether participants went back to work and changed something.

LearnBridge follows each participant through the full cycle and measures training at all four levels of the **Kirkpatrick evaluation model**:

| Level | Question | How LearnBridge measures it |
|---|---|---|
| 1. Reaction | Did participants value the course? | 1–5 rating and comments at course completion |
| 2. Learning | Did their skills improve? | The same skills self-assessment before and after training |
| 3. Behaviour | Did they use it at work? | A follow-up survey 90 days after the course |
| 4. Results | Did anything change in their organisation? | Follow-up questions on organisational change, plus short field stories |

## Features

**Participant view**

1. **Assess**: rate confidence in six competency areas (e.g. SDG localization, data for policymaking, climate resilience). A radar chart shows the profile, and the two weakest areas get course recommendations.
2. **Learn**: enroll in courses, work through modules, track progress, and rate the course when finished.
3. **Reassess**: answer the same questions again, with the first answers marked, and see a before/after comparison.
4. **Report back**: a 90-day follow-up on whether the training was used at work, what changed, or what got in the way.

**Training team view**

- **Impact ladder**: shows how many participants reach each Kirkpatrick level. Every percentage is out of everyone who enrolled, so drop-off at each stage stays visible.
- Skills before and after, reasons participants had not applied the training, and a per-course table (completion, rating, average skill gain, reported change).
- Field stories from follow-up responses.
- Filter by course, and **export to CSV** (one row per enrollment) for further analysis.

Entries made in the participant view are added to the training team view in real time, so the full cycle can be demonstrated in one session.

## Evaluation report (Python)

`analyze.py` turns the exported CSV into a Markdown report with charts:

- the Kirkpatrick funnel;
- paired t-tests and effect sizes (Cohen's dz) for each skill, before vs after;
- average gain in each course's target skill, tested against zero;
- a Spearman correlation between course rating and learning gain, to check whether satisfaction tracks learning;
- the barriers that stopped participants applying what they learned;
- notes on the limits of the evidence (self-rating, voluntary follow-up, no control group).

```bash
pip install -r requirements.txt
python analyze.py                        # sample data -> report.md and charts
python analyze.py my_export.csv -o out/  # your own export from the training team view
```

In the sample data, 63% of participants rated their course highly but only 27% reported a change in their organisation, and course ratings were only weakly related to learning gains. That gap is the reason to measure beyond Level 1.

## Tech stack

- Front end: HTML, CSS and vanilla JavaScript in a single file; charts with Chart.js
- Storage: browser `localStorage` (data stays on the participant's device in this prototype)
- Analysis: Python with pandas, SciPy and Matplotlib
- Hosting: GitHub Pages

## Project structure

```
learnbridge/
├── index.html          # the whole web app
├── README.md
├── analyze.py          # evaluation report generator
├── requirements.txt
├── sample_data.csv     # export of the simulated cohort
├── report.md           # generated evaluation report
└── funnel.png, skills.png, barriers.png   # report charts
```

## Design decisions

- **Two roles, no login.** A toggle switches between participant and training team, which keeps the demo usable in seconds while showing both sets of user needs.
- **Mobile first.** Many participants in regional training programmes join from their phones, so every view works on a small screen, in light and dark mode.
- **Honest denominators.** The impact ladder uses enrolled participants as the base for every level, rather than the number who answered each question, so results are not flattered by who chose to reply.
- **Simulated but realistic data.** The demo includes 120 simulated participants generated from a fixed random seed, so the dashboard is the same every time it is opened.

## Maintenance notes

- Reference data (skills, courses, modules, barriers) is defined at the top of the script in `index.html`. Adding a course means adding one entry to `COURSES`.
- The simulated cohort is produced by `buildSeed()`; change the seed number to generate a different cohort.
- Participant data is stored under the `learnbridge-v1` key in `localStorage`. Changing the data structure should come with a new key, so old saved data does not break the page.
- The CSV column names are the contract between the web app and `analyze.py`; change both together.

## Limitations and next steps

- Data is stored in the browser only. A production version would need a backend database, user accounts, and data protection measures appropriate for participant information.
- The 90-day follow-up is opened manually in the demo; in production it would be sent automatically by email.
- Skills are self-assessed. Adding short knowledge checks or supervisor feedback would strengthen Level 2 and Level 3 evidence.
- Planned: multilingual interface, offline support for low-bandwidth settings, and automated reminders.

## About

Built by **Gu Jinrong** (Big Data Management and Application, Nanjing University of Finance and Economics / Massey University) as a portfolio project. Development was AI-assisted: I worked with an AI assistant to design and write the code, then reviewed, tested and adapted it myself, and I can explain and maintain every part of it.

All participant data in this repository is simulated.
