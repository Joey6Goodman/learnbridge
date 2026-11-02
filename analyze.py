"""
LearnBridge evaluation report generator.

Reads the CSV exported from the LearnBridge "Training team" view and writes an
evaluation report (Markdown + charts) structured around the Kirkpatrick model:

  Level 1  Reaction   - did participants rate the course 4 or 5 out of 5?
  Level 2  Learning   - did their self-rated target skill rise by at least one level?
  Level 3  Behaviour  - did they use it at work within 90 days?
  Level 4  Results    - did they report a change in their team or organisation?

Usage:
    python analyze.py                          # uses sample_data.csv, writes to report/
    python analyze.py my_export.csv -o out/    # your own export

Requires: pandas, scipy, matplotlib, tabulate  (pip install -r requirements.txt)
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render charts without a display
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

SKILLS = {
    "sdg": "SDG localization",
    "data": "Data for policy",
    "climate": "Climate resilience",
    "digital": "Digital services",
    "stake": "Stakeholders",
    "pm": "Project M&E",
}
BARRIERS = {
    "no_chance": "No chance to use it yet",
    "support": "Not enough support from my team",
    "practice": "I need more practice",
    "other": "Something else",
}
BEFORE, AFTER = "#7C8B9A", "#D29500"


def load(path: Path) -> pd.DataFrame:
    """Load the export and add one helper column per enrollment."""
    df = pd.read_csv(path)
    # Gain in the skill each course is designed to build (NaN if no post-check)
    df["target_gain"] = df.apply(
        lambda r: r[f"post_{r.target_skill}"] - r[f"pre_{r.target_skill}"], axis=1
    )
    return df


def funnel(df: pd.DataFrame) -> pd.DataFrame:
    """Kirkpatrick funnel: every percentage is out of everyone who enrolled."""
    n = len(df)
    rows = [
        ("Enrolled", "Started the course", n),
        ("Reaction", "Rated the course 4 or 5", int((df.rating >= 4).sum())),
        ("Learning", "Target skill up by 1+ level",
         int(((df.completed == 1) & (df.target_gain >= 1)).sum())),
        ("Behaviour", "Used it at work within 90 days",
         int(df.followup_applied.isin(["regular", "once"]).sum())),
        ("Results", "Reported an organisational change", int((df.org_change == 1).sum())),
    ]
    out = pd.DataFrame(rows, columns=["Level", "Measure", "Count"])
    out["Share of enrolled"] = (out["Count"] / n * 100).round(1)
    return out


def skill_change(df: pd.DataFrame) -> pd.DataFrame:
    """Paired before/after comparison per skill, one row per participant."""
    people = df.drop_duplicates("participant_id")
    people = people.dropna(subset=[f"post_{s}" for s in SKILLS])
    rows = []
    for key, name in SKILLS.items():
        pre, post = people[f"pre_{key}"], people[f"post_{key}"]
        diff = post - pre
        t, p = stats.ttest_rel(post, pre)
        dz = diff.mean() / diff.std(ddof=1) if diff.std(ddof=1) > 0 else float("nan")
        rows.append([name, len(people), pre.mean(), post.mean(), diff.mean(), dz, p])
    return pd.DataFrame(rows, columns=["Skill", "n", "Before", "After", "Change",
                                       "Effect size (dz)", "p-value"])


def by_course(df: pd.DataFrame) -> pd.DataFrame:
    """Completion, satisfaction, learning and results for each course."""
    rows = []
    for (cid, title), g in df.groupby(["course_id", "course"]):
        done = g[g.completed == 1]
        gains = done.target_gain.dropna()
        p = stats.ttest_1samp(gains, 0).pvalue if len(gains) > 2 and gains.std() > 0 else float("nan")
        rows.append([title, len(g), done.shape[0] / len(g) * 100, done.rating.mean(),
                     gains.mean(), p, (g.org_change == 1).sum() / len(g) * 100])
    return pd.DataFrame(rows, columns=["Course", "Enrolled", "Completed %", "Avg rating",
                                       "Avg target gain", "p-value", "Reported change %"])


def rating_vs_learning(df: pd.DataFrame):
    """Does liking a course go together with learning from it? (Spearman)"""
    d = df[(df.completed == 1)].dropna(subset=["rating", "target_gain"])
    rho, p = stats.spearmanr(d.rating, d.target_gain)
    return rho, p, len(d)


def charts(df, fun, skills, outdir: Path):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

    # 1. Funnel
    fig, ax = plt.subplots(figsize=(7, 3.2))
    colors = [BEFORE] + [AFTER] * 4
    ax.barh(fun.Level[::-1], fun["Share of enrolled"][::-1], color=colors[::-1])
    for i, (v, c) in enumerate(zip(fun["Share of enrolled"][::-1], fun.Count[::-1])):
        ax.text(v + 1, i, f"{v:.0f}%  (n={c})", va="center")
    ax.set_xlim(0, 115)
    ax.set_xlabel("% of enrolled participants")
    ax.set_title("From enrollment to results (Kirkpatrick levels)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(outdir / "funnel.png", dpi=150)
    plt.close(fig)

    # 2. Skills before and after
    fig, ax = plt.subplots(figsize=(7, 3.4))
    x = range(len(skills))
    ax.bar([i - 0.2 for i in x], skills.Before, 0.4, label="Before", color=BEFORE)
    ax.bar([i + 0.2 for i in x], skills.After, 0.4, label="After", color=AFTER)
    ax.set_xticks(list(x), skills.Skill, rotation=20, ha="right")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Average self-rating (1–5)")
    ax.set_title("Self-rated skills before and after training")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(outdir / "skills.png", dpi=150)
    plt.close(fig)

    # 3. Barriers
    counts = df.barrier.map(BARRIERS).value_counts()
    if not counts.empty:
        fig, ax = plt.subplots(figsize=(7, 2.6))
        ax.barh(counts.index[::-1], counts.values[::-1], color="#2E6B5E")
        ax.set_xlabel("Participants")
        ax.set_title("Why participants had not used the training yet")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(outdir / "barriers.png", dpi=150)
        plt.close(fig)


def fmt_p(p):
    return "n/a" if pd.isna(p) else ("< 0.001" if p < 0.001 else f"{p:.3f}")


def write_report(df, fun, skills, courses, rho_p_n, outdir: Path):
    rho, p_rho, n_rho = rho_p_n
    respondents = df.followup_applied.notna().sum()
    completers = int((df.completed == 1).sum())
    best = courses.sort_values("Avg target gain", ascending=False).iloc[0]
    biggest_drop = (fun.Count.shift(1) - fun.Count).iloc[1:].idxmax()

    sk = skills.copy()
    for c in ["Before", "After", "Change", "Effect size (dz)"]:
        sk[c] = sk[c].round(2)
    sk["p-value"] = sk["p-value"].map(fmt_p)
    co = courses.copy()
    co["Completed %"] = co["Completed %"].round(0).astype(int)
    co["Reported change %"] = co["Reported change %"].round(0).astype(int)
    for c in ["Avg rating", "Avg target gain"]:
        co[c] = co[c].round(2)
    co["p-value"] = co["p-value"].map(fmt_p)

    lines = [
        "# LearnBridge Training Evaluation Report",
        "",
        f"Data: {len(df)} enrollments from {df.participant_id.nunique()} participants "
        f"across {df.course_id.nunique()} courses. {respondents} of {completers} participants "
        "who completed a course answered the 90-day follow-up.",
        "",
        "> The sample data is simulated for demonstration. Run the script on a real export to "
        "produce the same report for an actual programme.",
        "",
        "## Key findings",
        "",
        f"- **{fun.iloc[4]['Share of enrolled']:.0f}% of enrolled participants reported a change in "
        f"their organisation**, against {fun.iloc[1]['Share of enrolled']:.0f}% who rated their course "
        "highly. Satisfaction scores alone would overstate the programme's impact.",
        f"- The largest drop-off is between **{fun.Level[biggest_drop - 1]}** and "
        f"**{fun.Level[biggest_drop]}**, so that is where extra support would help most.",
        f"- Self-rated skills rose in {(skills.Change > 0).sum()} of {len(skills)} areas "
        f"({(skills['p-value'] < 0.05).sum()} statistically significant at p < 0.05); the largest "
        f"average gain was in **{skills.sort_values('Change').iloc[-1].Skill}**.",
        f"- **{best.Course}** produced the highest average gain in its target skill "
        f"(+{best['Avg target gain']:.2f} levels).",
        f"- Rating and learning gain are {'only weakly' if abs(rho) < 0.3 else 'clearly'} related "
        f"(Spearman ρ = {rho:.2f}, p = {fmt_p(p_rho)}, n = {n_rho}): liking a course is not the same "
        "as learning from it.",
        "",
        "## 1. From enrollment to results",
        "",
        "![Funnel](funnel.png)",
        "",
        fun.to_markdown(index=False),
        "",
        "## 2. Did skills improve?",
        "",
        "Paired comparison of each participant's first and second self-assessment. "
        "dz is the mean change divided by the standard deviation of the change.",
        "",
        "![Skills](skills.png)",
        "",
        sk.to_markdown(index=False),
        "",
        "## 3. Results by course",
        "",
        "Average target gain is the change in the skill each course is designed to build, "
        "among participants who completed it; the p-value tests whether that gain differs from zero.",
        "",
        co.to_markdown(index=False),
        "",
        "## 4. What got in the way",
        "",
        "![Barriers](barriers.png)",
        "",
        "## Notes and limitations",
        "",
        "- Skills are self-rated, so gains may partly reflect confidence rather than ability.",
        "- Follow-up responses are voluntary; participants who applied the training may be more "
        "likely to reply, which would inflate Levels 3 and 4.",
        "- There is no control group, so the analysis shows change after training, not proof "
        "that the training caused it.",
        "",
    ]
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser(description="Generate a LearnBridge evaluation report.")
    ap.add_argument("csv", nargs="?", default=here / "sample_data.csv", type=Path)
    ap.add_argument("-o", "--out", default=here / "report", type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    df = load(args.csv)
    fun, skills, courses = funnel(df), skill_change(df), by_course(df)
    charts(df, fun, skills, args.out)
    write_report(df, fun, skills, courses, rating_vs_learning(df), args.out)
    print(f"Report written to {args.out / 'report.md'}")


if __name__ == "__main__":
    main()
