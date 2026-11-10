"""Tiny, entirely FICTIONAL paper-curation fixture for Gate 4C. Public and synthetic.

No real paper, author, venue, result or user data: every title and number below
is invented. Split limitations, stated plainly:
* experience (2 notes) and development (2 tasks) were hand-written together by one
  author, so the development tasks are NOT an independent holdout;
* two items per split cannot support any statistic;
* there is no final/holdout split in this fixture at all;
* EVALUATOR_KEY encodes fake-provider behavior, not curation quality.
Experience notes and consolidated claims contain no task answers; the key is
read only by the trusted local evaluator and never placed in a request.
"""

# event_id -> fictional raw curation note (stored as evidence source bytes)
EXPERIENCE_SOURCES = {
    "e-1": ("FICTIONAL NOTE. Invented preprint 'Glass Owls Prefer Tuesdays' (no such paper). "
            "Curator log: the headline claim was copied before the invented sample size "
            "was checked, and the entry had to be redone."),
    "e-2": ("FICTIONAL NOTE. Invented preprint 'Tidal Lanterns in Paper Seas' (no such paper). "
            "Curator log: the entry recorded the invented dataset licence line first and "
            "needed no rework."),
}

# memory_id -> (evidence event_id, consolidated claim); general lessons, no task answers
CONSOLIDATED_CLAIMS = {
    "m-1": ("e-1", "fictional curation lesson: check the stated sample size before "
                   "copying a headline claim"),
    "m-2": ("e-2", "fictional curation lesson: record the dataset licence line early"),
}

# development tasks: prompts only, about different invented papers
TASKS = [
    {"task_id": "paper-task-1",
     "prompt": "Fictional curation task: draft an entry for the invented preprint "
               "'Copper Rain Over Quiet Looms'."},
    {"task_id": "paper-task-2",
     "prompt": "Fictional curation task: draft an entry for the invented preprint "
               "'Seven Doors of a Folding Moon'."},
]

# trusted-evaluator side only
EVALUATOR_KEY = {"paper-task-1": b"fixture-reply-with-records",
                 "paper-task-2": b"fixture-reply-with-records"}
