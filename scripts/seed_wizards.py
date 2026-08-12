"""
Seed the guided workflows ("wizards") that ship with the product.

Five real, publishable workflows with bilingual (en/fa) presentation text and
written-out `guideline_prompt`s that drive the shared `AcademicAgent` through
the app's actual tools. This is content, not schema: the tables are created by
`init_models()` on startup — this script only fills them.

    # against a local backend (.env's DATABASE_URL)
    uv run python scripts/seed_wizards.py

    # against the docker-compose stack
    docker compose exec app uv run python scripts/seed_wizards.py

Idempotent. A wizard is matched by `slug`: missing ones are created, existing
ones have their presentation fields refreshed, and their steps are left alone —
an admin's edits in the wizard editor always win. Pass `--replace-steps` to
rewrite the steps of the seeded wizards anyway; that is refused for any wizard
users have already run, so a live run can never lose the step it is sitting on.

Nothing here is published automatically unless `--publish` is passed: the
default is to create the workflows unpublished so an admin can read them over
in the editor first.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any, Dict, List

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal, init_models
from app.models.wizard import Wizard, WizardRun, WizardStep


# --------------------------------------------------------------------------- #
# The content
# --------------------------------------------------------------------------- #
# `guideline_prompt` is written for the model, not the user: it never appears in
# the UI. It is re-injected on every turn of its step (`build_step_guidance`),
# which also handles the reply language and the step-complete marker — so the
# prompts below say what to do, not what language to speak or when to announce
# a transition.
WIZARDS: List[Dict[str, Any]] = [
    {
        "slug": "systematic-review",
        "name": "systematic review",
        "icon": "search",
        "position": 1,
        "title_en": "Run a systematic literature review",
        "title_fa": "اجرای مرور نظام‌مند ادبیات",
        "short_description_en": (
            "From a vague interest to a screened, evidence-backed review: shape "
            "the question, build the search, screen the abstracts, ingest what "
            "you keep, and write it up with citations that check out."
        ),
        "short_description_fa": (
            "از یک علاقهٔ کلی تا مرور مستند و غربال‌شده: ساختن پرسش پژوهش، طراحی "
            "راهبرد جست‌وجو، غربالگری چکیده‌ها، بارگذاری مقاله‌های منتخب و نگارش "
            "مرور با ارجاع‌های راستی‌آزمایی‌شده."
        ),
        "steps": [
            {
                "name_en": "Define the review question",
                "name_fa": "تعریف پرسش مرور",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: turn the user's broad interest into ONE answerable "
                    "review question, with explicit inclusion and exclusion "
                    "criteria.\n\n"
                    "Ask about the field, the population or setting, what is "
                    "being compared, and the outcome that matters — one or two "
                    "questions per message, never an interrogation. Offer a "
                    "structured framing (PICO for clinical work, SPIDER for "
                    "qualitative, or a plain population/context/outcome triple) "
                    "and let the user pick.\n\n"
                    "Push back on questions that are too broad to review "
                    "('everything about AI in education') and say concretely "
                    "how to narrow them: a population, a time window, a "
                    "language, a study design.\n\n"
                    "End by writing the final question plus the inclusion and "
                    "exclusion criteria as a short numbered list the user can "
                    "copy — the next steps depend on this list existing."
                ),
            },
            {
                "name_en": "Build the search strategy",
                "name_fa": "ساخت راهبرد جست‌وجو",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: convert the agreed question into real searches and a "
                    "candidate set of papers.\n\n"
                    "Build Boolean queries from the question's concepts — "
                    "synonyms and field-specific terms per concept, OR within a "
                    "concept, AND between concepts. Show the query string "
                    "itself so the user can reuse it in their own database.\n\n"
                    "Run the searches with `search_literature`, `search_scopus` "
                    "and `search_openalex`. Report results as a compact table: "
                    "title, first author, year, venue, DOI. Say how many hits "
                    "each query returned and which query you would keep.\n\n"
                    "If the yield is tiny or enormous, adjust the query with "
                    "the user rather than silently accepting it. Finish with a "
                    "candidate list ready for screening."
                ),
            },
            {
                "name_en": "Screen the abstracts",
                "name_fa": "غربالگری چکیده‌ها",
                "max_messages": 10,
                "guideline_prompt": (
                    "Goal: decide, against the criteria from step 1, which "
                    "candidates are worth reading in full.\n\n"
                    "The user brings a CSV of abstracts (a database export, or "
                    "the candidate list from the previous step). Confirm the "
                    "file with `list_session_files`, then run "
                    "`screen_abstracts_csv` with the inclusion and exclusion "
                    "criteria stated verbatim — do not paraphrase them into "
                    "something looser.\n\n"
                    "Explain the returned workbook: what the colour of each row "
                    "means and where the reason for each decision is written. "
                    "Walk the borderline rows with the user and let them "
                    "overrule a decision; record the overrule.\n\n"
                    "Finish with the list of studies that made it through, and "
                    "the count excluded at this stage — a review has to report "
                    "both."
                ),
            },
            {
                "name_en": "Ingest the included papers",
                "name_fa": "بارگذاری مقاله‌های منتخب",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: get the full text of every included study into the "
                    "corpus so later steps can quote it.\n\n"
                    "For PDFs the user uploads, call `ingest_pdf`. For a study "
                    "they only have a DOI for, try "
                    "`find_and_ingest_open_access_pdf`. Confirm each one after "
                    "it lands, and keep a running list of what is in and what "
                    "is still missing.\n\n"
                    "When a paper cannot be retrieved, say so plainly and move "
                    "on — never work from the abstract as if it were the full "
                    "text.\n\n"
                    "Spot-check the corpus with `search_my_papers` on a term "
                    "from the question, so the user can see retrieval works "
                    "before relying on it."
                ),
            },
            {
                "name_en": "Build the evidence table",
                "name_fa": "ساخت جدول شواهد",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: turn the included papers into one comparable table — "
                    "the backbone of the review's synthesis.\n\n"
                    "For each study, use `summarize_paper` and "
                    "`search_my_papers` to extract: design, setting, sample "
                    "size, what was measured, the headline result with its "
                    "numbers, and the limitations the authors admit to. Keep "
                    "the citation attached to every row.\n\n"
                    "Then read across the table with the user: where studies "
                    "agree, where they conflict, and what nobody has looked at "
                    "yet. That gap is what the review argues from.\n\n"
                    "Never fill a cell you could not find in the text — write "
                    "'not reported', which is itself a finding."
                ),
            },
            {
                "name_en": "Write the review",
                "name_fa": "نگارش مرور",
                "max_messages": 12,
                "guideline_prompt": (
                    "Goal: draft the review, section by section, grounded in "
                    "the ingested corpus.\n\n"
                    "Agree the citation style (IEEE, APA or Vancouver) and the "
                    "section list first — `plan_paper_sections` or "
                    "`generate_paper_outline` if the user has no structure in "
                    "mind. Then draft ONE section per turn with "
                    "`draft_paper_section`, and stop for the user's reaction "
                    "before the next.\n\n"
                    "Every claim about a study must carry its citation. Run "
                    "`validate_references` before the user takes the text "
                    "anywhere, and report anything that failed to resolve "
                    "rather than quietly dropping it.\n\n"
                    "When the user asks for the finished document, call "
                    "`compile_paper` and give them the download."
                ),
            },
        ],
    },
    {
        "slug": "analyse-my-data",
        "name": "analyse my data",
        "icon": "chart",
        "position": 2,
        "title_en": "Analyse your dataset",
        "title_fa": "تحلیل مجموعه‌دادهٔ شما",
        "short_description_en": (
            "Bring a CSV and leave with a defensible analysis: the data "
            "described, cleaned, tested with the right method, plotted, and "
            "written up as a Results section."
        ),
        "short_description_fa": (
            "با یک فایل CSV شروع کنید و با تحلیلی قابل‌دفاع تمام کنید: توصیف و "
            "پاکسازی داده، انتخاب آزمون مناسب، رسم نمودار و نگارش بخش نتایج."
        ),
        "steps": [
            {
                "name_en": "Describe the dataset",
                "name_fa": "معرفی مجموعه‌داده",
                "max_messages": 6,
                "guideline_prompt": (
                    "Goal: understand the data before touching it.\n\n"
                    "Find the uploaded file with `list_session_files` and read "
                    "its shape with `get_csv_info`. Report the columns, their "
                    "types, the row count and the share of missing values.\n\n"
                    "Then ask the user what you cannot see: what each variable "
                    "actually measures, in what units, how the data was "
                    "collected, and which column is the outcome they care "
                    "about. Ask about the study design — repeated measures, "
                    "groups, time series — because it decides the whole "
                    "analysis.\n\n"
                    "Finish with a short data dictionary in your own words and "
                    "have the user confirm it."
                ),
            },
            {
                "name_en": "Clean and explore",
                "name_fa": "پاکسازی و کاوش داده",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: a dataset you can trust, and a first look at what is "
                    "in it.\n\n"
                    "Use `analytics_sandbox` to check distributions, missing "
                    "values, impossible values, duplicates and outliers. Show "
                    "the code you ran — the user has to be able to defend "
                    "it.\n\n"
                    "Propose each cleaning decision before making it, with its "
                    "consequence: dropping rows costs power, imputing invents "
                    "data, winsorising changes the tails. The user decides; you "
                    "record what was changed and how many rows it touched.\n\n"
                    "End with descriptive statistics for every variable that "
                    "will enter the analysis."
                ),
            },
            {
                "name_en": "Run the analysis",
                "name_fa": "اجرای تحلیل",
                "max_messages": 10,
                "guideline_prompt": (
                    "Goal: answer the user's actual question with a method that "
                    "fits their design.\n\n"
                    "State the hypothesis in testable form first. Pick the test "
                    "from the design and the variable types, say why that test "
                    "and not the obvious alternative, and check its assumptions "
                    "with `analytics_sandbox` before trusting its output.\n\n"
                    "Report effect sizes and confidence intervals alongside "
                    "p-values, and say what the result means in the units of "
                    "the problem. If an assumption fails, offer the robust or "
                    "non-parametric alternative and rerun.\n\n"
                    "Never present a result you did not compute in the sandbox, "
                    "and never round a finding into something stronger than the "
                    "numbers support."
                ),
            },
            {
                "name_en": "Make the figures",
                "name_fa": "ساخت نمودارها",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: figures that carry the finding on their own.\n\n"
                    "Build each plot in `analytics_sandbox`; they are saved to "
                    "`output_figures/` and the user can download them. One "
                    "message, one figure, then ask what to change.\n\n"
                    "Match the chart to the claim: distributions for spread, "
                    "not bar charts of means; a paired plot when the data is "
                    "paired. Always label both axes with units, keep the "
                    "categories readable, and never use colour as the only way "
                    "to tell series apart.\n\n"
                    "Write a caption for each figure in the style of a journal "
                    "figure legend: what is shown, n, and what the error bars "
                    "represent."
                ),
            },
            {
                "name_en": "Write the results section",
                "name_fa": "نگارش بخش نتایج",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: a Results section made only of what the analysis "
                    "produced.\n\n"
                    "Draft it with `draft_paper_section`, using the numbers "
                    "computed in this run — figures referenced by name, tests "
                    "reported with their statistic, degrees of freedom, effect "
                    "size and interval. No value may appear that the sandbox "
                    "did not print.\n\n"
                    "Keep interpretation out of Results; offer to draft a "
                    "separate Discussion paragraph if the user wants the "
                    "'so what'.\n\n"
                    "Finish by listing the limitations the analysis itself "
                    "exposed — sample size, missing data, assumptions that were "
                    "shaky."
                ),
            },
        ],
    },
    {
        "slug": "understand-a-paper",
        "name": "understand a paper",
        "icon": "document",
        "position": 3,
        "title_en": "Understand a paper deeply",
        "title_fa": "درک عمیق یک مقاله",
        "short_description_en": (
            "Read one paper properly: ingest it, get a structured summary, "
            "interrogate its method, see where it sits in the literature, and "
            "leave with quotable, citable notes."
        ),
        "short_description_fa": (
            "یک مقاله را درست بخوانید: بارگذاری، خلاصهٔ ساختاریافته، نقد روش، "
            "جایگاه آن در ادبیات پژوهش، و برداشت نهایی همراه با ارجاع‌های آماده."
        ),
        "steps": [
            {
                "name_en": "Bring the paper in",
                "name_fa": "افزودن مقاله",
                "max_messages": 5,
                "guideline_prompt": (
                    "Goal: get the full text into the corpus and confirm what "
                    "the paper is.\n\n"
                    "If the user uploads a PDF, call `ingest_pdf`. If they give "
                    "a DOI or a title, resolve it with `resolve_citation` and "
                    "try `find_and_ingest_open_access_pdf`.\n\n"
                    "Confirm the metadata back to them — authors, year, venue, "
                    "DOI — so a wrong paper is caught now rather than five "
                    "messages later. If only the abstract is available, say so "
                    "explicitly and agree with the user whether to continue on "
                    "that basis."
                ),
            },
            {
                "name_en": "Structured summary",
                "name_fa": "خلاصهٔ ساختاریافته",
                "max_messages": 6,
                "guideline_prompt": (
                    "Goal: the paper in plain language, with nothing important "
                    "left out.\n\n"
                    "Use `summarize_paper` and give: the problem it addresses, "
                    "what the authors did, the data they used, what they found "
                    "with the actual numbers, what they claim it means, and the "
                    "limitations they acknowledge.\n\n"
                    "Define the field's jargon the first time it appears. Where "
                    "the paper is genuinely unclear, say that it is unclear "
                    "rather than smoothing it over.\n\n"
                    "Ask the user which part they want expanded before moving "
                    "on."
                ),
            },
            {
                "name_en": "Interrogate the method",
                "name_fa": "نقد روش",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: judge whether the paper's conclusions are earned.\n\n"
                    "Work through the design: does it support a causal claim or "
                    "only an associational one? Is the sample big enough and "
                    "representative of the population claimed? Are the measures "
                    "valid? Are the statistics appropriate, and were their "
                    "assumptions checked? Is there a control, a baseline, a "
                    "pre-registration?\n\n"
                    "Use `search_my_papers` to quote the passage behind each "
                    "point — a critique without the sentence it refers to is "
                    "worthless.\n\n"
                    "Be fair: name what the paper does well too, and separate "
                    "'this is a flaw' from 'this is a limitation the authors "
                    "already state'."
                ),
            },
            {
                "name_en": "Place it in the literature",
                "name_fa": "جایگاه آن در ادبیات",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: the paper as one point in a conversation, not an "
                    "isolated fact.\n\n"
                    "Use `search_literature` and `search_openalex` to find what "
                    "it builds on, what has cited it since, and which studies "
                    "reach a different conclusion. Show the comparison as a "
                    "short table: study, year, what it found, how it differs "
                    "from this one.\n\n"
                    "Say where the field currently stands and what remains "
                    "contested. Point out if the paper is old enough that its "
                    "conclusions have likely been superseded."
                ),
            },
            {
                "name_en": "Take what you need",
                "name_fa": "برداشت نهایی",
                "max_messages": 6,
                "guideline_prompt": (
                    "Goal: notes the user can actually use in their own "
                    "work.\n\n"
                    "Produce the handful of claims worth citing, each with the "
                    "exact citation and a one-line note on what it supports. "
                    "Provide the BibTeX entry via `resolve_citation`.\n\n"
                    "Then connect it to the user's project: which section of "
                    "their paper this belongs in, and what it lets them argue. "
                    "If it undercuts something they believed, say so."
                ),
            },
        ],
    },
    {
        "slug": "research-proposal",
        "name": "research proposal",
        "icon": "compass",
        "position": 4,
        "title_en": "Write a research proposal",
        "title_fa": "نگارش پروپوزال پژوهشی",
        "short_description_en": (
            "Turn an idea into a proposal a committee will accept: a sharp "
            "question, an evidenced gap, a method that survives scrutiny, a "
            "realistic timeline, and the written document."
        ),
        "short_description_fa": (
            "ایدهٔ خود را به پروپوزالی قابل‌دفاع تبدیل کنید: پرسش دقیق، خلأ "
            "پژوهشی مستند، روش قابل‌دفاع، زمان‌بندی واقع‌بینانه و متن نهایی."
        ),
        "steps": [
            {
                "name_en": "Sharpen the idea",
                "name_fa": "شفاف‌سازی ایده",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: one specific, feasible research question with stated "
                    "objectives.\n\n"
                    "Start from what the user is curious about and narrow it "
                    "with them: population, context, variables, scale. Name the "
                    "constraints out loud — time, access to participants, "
                    "equipment, budget — because a proposal that ignores them "
                    "fails later.\n\n"
                    "Offer candidate titles with `suggest_paper_titles` once "
                    "the question is stable. Finish with the question, two to "
                    "four objectives, and the contribution stated in one "
                    "sentence."
                ),
            },
            {
                "name_en": "Evidence the gap",
                "name_fa": "مستندسازی خلأ پژوهشی",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: show, with citations, that this work has not already "
                    "been done.\n\n"
                    "Search with `search_literature`, `search_scopus` and "
                    "`search_openalex`: the foundational works, the most cited, "
                    "and the last two or three years. Group what you find into "
                    "the two or three lines of work that surround the "
                    "question.\n\n"
                    "Then state the gap precisely — not 'little research "
                    "exists', but which population, method or outcome nobody "
                    "has covered. If the search shows the work HAS been done, "
                    "tell the user immediately and help them pivot; that is the "
                    "single most valuable thing this step can do."
                ),
            },
            {
                "name_en": "Design the method",
                "name_fa": "طراحی روش",
                "max_messages": 10,
                "guideline_prompt": (
                    "Goal: a method section a reviewer could follow and "
                    "replicate.\n\n"
                    "Work through: design and why it fits the question; "
                    "participants or data sources and how they are recruited or "
                    "obtained; instruments and their validity; procedure step "
                    "by step; the analysis plan, named test by named test, "
                    "including how the sample size was decided; and ethics — "
                    "consent, anonymity, approvals.\n\n"
                    "Challenge anything unworkable at the user's scale and "
                    "offer a smaller design that still answers the question. "
                    "End with the threats to validity and how the design "
                    "mitigates them."
                ),
            },
            {
                "name_en": "Plan the work",
                "name_fa": "زمان‌بندی و منابع",
                "max_messages": 6,
                "guideline_prompt": (
                    "Goal: a timeline the user can defend and actually "
                    "follow.\n\n"
                    "Break the project into phases with deliverables, and use "
                    "`write_plan` so the plan persists beside the "
                    "conversation. Attach a duration to each phase and put the "
                    "dependencies in the right order — ethics approval before "
                    "recruitment, pilot before main collection.\n\n"
                    "Name the resources each phase needs and the risks that "
                    "could derail it, each with a mitigation. Be honest when a "
                    "timeline is optimistic."
                ),
            },
            {
                "name_en": "Draft the proposal",
                "name_fa": "نگارش پروپوزال",
                "max_messages": 10,
                "guideline_prompt": (
                    "Goal: the written document, assembled from the decisions "
                    "already made.\n\n"
                    "Lay out the sections with `generate_paper_outline` or "
                    "`plan_paper_sections`, then draft ONE section per turn "
                    "with `draft_paper_section`, pausing for the user's "
                    "reaction. Reuse the question, gap, method and timeline as "
                    "agreed — do not quietly reinvent them.\n\n"
                    "Run `validate_references` over the finished text, then "
                    "`compile_paper` when the user asks for the document."
                ),
            },
        ],
    },
    {
        "slug": "submit-to-a-journal",
        "name": "submit to a journal",
        "icon": "quote",
        "position": 5,
        "title_en": "Get ready to submit",
        "title_fa": "آماده‌سازی برای ارسال به مجله",
        "short_description_en": (
            "The last mile before submission: check the manuscript, verify "
            "every citation resolves, pick target venues, format to their "
            "requirements, and write the cover letter."
        ),
        "short_description_fa": (
            "آخرین گام پیش از ارسال: بازبینی دست‌نوشته، راستی‌آزمایی همهٔ ارجاع‌ها، "
            "انتخاب مجلهٔ هدف، قالب‌بندی بر اساس راهنمای مجله و نگارش نامهٔ همراه."
        ),
        "steps": [
            {
                "name_en": "Check the manuscript",
                "name_fa": "بازبینی دست‌نوشته",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: find what a desk-reject would find, before an editor "
                    "does.\n\n"
                    "Take the user's draft (uploaded, or ingested with "
                    "`ingest_pdf`) and review it section by section: does the "
                    "abstract state the contribution and the result? Does the "
                    "introduction end with the gap and the aim? Are the methods "
                    "reproducible? Do the results answer the questions asked? "
                    "Does the discussion overclaim?\n\n"
                    "Give concrete rewrites, not adjectives — quote the "
                    "sentence and show the replacement. Offer `humanize_text` "
                    "where the prose reads as stilted or machine-made.\n\n"
                    "Finish with a prioritised fix list: what must change "
                    "before submission, and what is optional polish."
                ),
            },
            {
                "name_en": "Verify every citation",
                "name_fa": "راستی‌آزمایی ارجاع‌ها",
                "max_messages": 6,
                "guideline_prompt": (
                    "Goal: no reference in the manuscript that does not "
                    "exist.\n\n"
                    "Run `validate_references` over the reference list and "
                    "report the outcome honestly: which resolved, which did "
                    "not, and which resolved to something different from what "
                    "was cited. Use `resolve_citation` to repair entries and to "
                    "fill in missing DOIs.\n\n"
                    "Treat an unresolvable reference as a blocker and say so — "
                    "a fabricated citation found by a reviewer costs far more "
                    "than one found here. Hand back the corrected list in the "
                    "user's citation style."
                ),
            },
            {
                "name_en": "Choose target venues",
                "name_fa": "انتخاب مجلهٔ هدف",
                "max_messages": 6,
                "guideline_prompt": (
                    "Goal: a realistic shortlist, in submission order.\n\n"
                    "Use `suggest_venues` from the paper's topic, method and "
                    "contribution. For each candidate give scope fit, indexing, "
                    "typical turnaround, open-access terms and any fee — and be "
                    "clear about what you cannot verify.\n\n"
                    "Ask what matters most to the user: speed, prestige, "
                    "readership, cost. Then propose three to five venues ranked "
                    "as a ladder — the ambitious first choice, the solid fit, "
                    "and the reliable fallback — with one line of reasoning "
                    "each."
                ),
            },
            {
                "name_en": "Format for the venue",
                "name_fa": "قالب‌بندی برای مجله",
                "max_messages": 8,
                "guideline_prompt": (
                    "Goal: a manuscript that matches the chosen journal's "
                    "requirements.\n\n"
                    "Work from the venue's author guidelines as the user "
                    "reports them: section order and headings, word and abstract "
                    "limits, keyword count, figure and table conventions, and "
                    "the required citation style. Convert the references with "
                    "`draft_paper_section`/`compile_paper` as needed and flag "
                    "every place the text exceeds a limit.\n\n"
                    "Produce the submission-ready document with `compile_paper` "
                    "and list anything the user must supply outside it — "
                    "declarations, data availability, author contributions."
                ),
            },
            {
                "name_en": "Write the cover letter",
                "name_fa": "نگارش نامهٔ همراه",
                "max_messages": 6,
                "guideline_prompt": (
                    "Goal: a short letter that makes the editor's decision "
                    "easy.\n\n"
                    "One page: what the paper shows, why it fits THIS journal's "
                    "scope and readership, why it matters now, and the "
                    "statements editors require — original work, not under "
                    "consideration elsewhere, conflicts of interest, ethics "
                    "approval where relevant.\n\n"
                    "Draft it in the user's voice and keep it factual; no "
                    "salesmanship, no claims the paper does not support. Offer "
                    "suggested reviewers with a reason for each, and note any "
                    "the user wants excluded."
                ),
            },
        ],
    },
]


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #
PRESENTATION_FIELDS = (
    "name",
    "icon",
    "position",
    "title_en",
    "title_fa",
    "short_description_en",
    "short_description_fa",
)


async def seed(*, replace_steps: bool, publish: bool) -> None:
    created = updated = skipped = 0

    async with AsyncSessionLocal() as db:
        for spec in WIZARDS:
            slug = spec["slug"]
            steps = spec["steps"]

            wizard = await db.scalar(select(Wizard).where(Wizard.slug == slug))
            if wizard is None:
                wizard = Wizard(
                    slug=slug,
                    is_published=publish,
                    **{f: spec[f] for f in PRESENTATION_FIELDS},
                )
                db.add(wizard)
                await db.flush()  # need the id for the steps
                for position, step in enumerate(steps):
                    db.add(WizardStep(wizard_id=wizard.id, position=position, **step))
                created += 1
                print(f"  created  {slug}  ({len(steps)} steps)")
                continue

            for field in PRESENTATION_FIELDS:
                setattr(wizard, field, spec[field])
            if publish:
                wizard.is_published = True

            step_count = await db.scalar(
                select(func.count(WizardStep.id)).where(
                    WizardStep.wizard_id == wizard.id
                )
            )
            if step_count and not replace_steps:
                updated += 1
                print(f"  updated  {slug}  (kept its {step_count} existing steps)")
                continue

            if step_count:
                # A run points at the step it is sitting on; deleting it would
                # strand that run mid-workflow.
                runs = await db.scalar(
                    select(func.count(WizardRun.id)).where(
                        WizardRun.wizard_id == wizard.id
                    )
                )
                if runs:
                    skipped += 1
                    print(
                        f"  skipped  {slug}  (--replace-steps refused: "
                        f"{runs} run(s) exist)"
                    )
                    continue
                existing = (
                    await db.scalars(
                        select(WizardStep).where(WizardStep.wizard_id == wizard.id)
                    )
                ).all()
                for step in existing:
                    await db.delete(step)
                await db.flush()

            for position, step in enumerate(steps):
                db.add(WizardStep(wizard_id=wizard.id, position=position, **step))
            updated += 1
            print(f"  updated  {slug}  ({len(steps)} steps written)")

        await db.commit()

    print(f"\n{created} created, {updated} updated, {skipped} skipped.")
    if not publish:
        print("Wizards are unpublished — publish them from the admin panel, or")
        print("re-run with --publish.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace-steps",
        action="store_true",
        help="rewrite the steps of seeded wizards that already have some "
        "(refused for wizards with existing runs)",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="publish the seeded wizards so they appear on the landing page",
    )
    args = parser.parse_args()

    async def run() -> None:
        await init_models()  # no-op when the tables already exist
        await seed(replace_steps=args.replace_steps, publish=args.publish)

    asyncio.run(run())


if __name__ == "__main__":
    main()
