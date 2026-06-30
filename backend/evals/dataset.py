EVAL_QUESTIONS = [
    {"question": "What machine learning courses does NUS offer?",       "expected_tools": ["search_modules_tool"]},
    {"question": "Find introductory data structures courses",           "expected_tools": ["search_modules_tool"]},
    {"question": "What computer vision modules are available?",         "expected_tools": ["search_modules_tool"]},
    {"question": "I want to become a data scientist, what should I take?", "expected_tools": ["search_modules_tool"]},
    {"question": "Show me NLP courses",                                 "expected_tools": ["search_modules_tool"]},
    {"question": "What finance courses can I take at NUS?",             "expected_tools": ["search_modules_tool"]},
    {"question": "I'm interested in cybersecurity modules",             "expected_tools": ["search_modules_tool"]},
    {"question": "What courses cover software engineering practices?",  "expected_tools": ["search_modules_tool"]},
    {"question": "Recommend courses for someone interested in AI research", "expected_tools": ["search_modules_tool"]},
    {"question": "What statistics modules are offered by SoC?",         "expected_tools": ["find_departments_tool", "search_modules_tool"]},
    {"question": "Which computing Master's courses are relevant for AI specialization?", "expected_tools": ["find_departments_tool", "search_modules_tool"]},
    {"question": "Which computing undergard courses teach neural networks at an introductory level?", "expected_tools": ["find_departments_tool", "search_modules_tool"]},
    {"question": "Which computing phd courses cover security", "expected_tools": ["find_departments_tool", "search_modules_tool"]},
    {"question": "Suggest robotics courses for a Master's student in School of computing", "expected_tools": ["find_departments_tool", "search_modules_tool"]},

    # Course tracking — single turn
    {"question": "I've already taken CS1101S and MA1521.",              "expected_tools": ["update_courses_taken"]},
    {"question": "I completed CS2040S last semester.",                  "expected_tools": ["update_courses_taken"]},
    {"question": "Add CS3244 to my planned courses.",                   "expected_tools": ["update_courses_planned"]},
    {"question": "I'm planning to take CS4248 and CS4211.",            "expected_tools": ["update_courses_planned"]},
    {"question": "Remove MA1521 from my completed courses.",            "expected_tools": ["update_courses_taken"]},
    {"question": "Clear all my planned courses.",                       "expected_tools": ["update_courses_planned"]},
    {"question": "I've taken CS1101S. What ML courses should I take next?", "expected_tools": ["update_courses_taken", "search_modules_tool"]},
    {"question": "I'm planning CS3244 — are there prereqs I should take first?", "expected_tools": ["update_courses_planned", "get_module_tool"]},

    # get_module_tool — direct code lookup
    {"question": "What are the prerequisites for CS3244?",                "expected_tools": ["get_module_tool"]},
    {"question": "Tell me about MA1521",                                  "expected_tools": ["get_module_tool"]},
    {"question": "How many credits is CS2040S?",                          "expected_tools": ["get_module_tool"]},

    # Course tracking — multi-turn (uses messages list)
    {"messages": ["I've already taken CS1101S.", "What ML courses should I take?"],
     "expected_tools": ["update_courses_taken", "search_modules_tool"],
     "expected_courses_taken": ["CS1101S"], "expected_courses_planned": []},
    {"messages": ["I'm planning to take CS3244.", "Actually, I've already completed CS3244."],
     "expected_tools": ["update_courses_planned", "get_module_tool", "update_courses_taken"],
     "expected_courses_taken": ["CS3244"], "expected_courses_planned": []},
    {"messages": ["I've taken CS1101S.", "Add CS3244 to my plan.", "What should I take after CS3244?"],
     "expected_tools": ["update_courses_taken", "update_courses_planned", "get_module_tool", "search_modules_tool"],
     "expected_courses_taken": ["CS1101S"], "expected_courses_planned": ["CS3244"]},
]


# Labeled dataset for the RETRIEVAL eval (recall@k / MRR / precision@k). Distinct
# from EVAL_QUESTIONS above: this tests `search_modules` DIRECTLY (no agent, no
# LLM), so we can isolate retrieval failures from tool-routing/generation failures.
#
# `query` is the search string the tool actually receives (already reformulated
# from any user utterance), NOT a conversational question. `relevant` is the
# module code(s) that SHOULD be retrieved.
#
# TWO GROUPS (different jobs):
#   - REALISTIC: department + min_level filters set. Mirrors the production agent
#     path (find_departments_tool runs first), keeps the candidate pool small so
#     labels are tractable and precision@k is meaningful. `min_level` is set to
#     the lowest relevant code's level so the filter never excludes a label.
#   - HARD-PROBE: NO filters. Kept deliberately to stay sensitive to the step-2
#     embedding fix — the dept filter removes the cross-department competitors
#     that the doc_text cleanup targets, so an all-filtered set would mask whether
#     the embedding itself improved. These are how we prove step 2 worked.
#
# Labeling notes:
#   - `relevant` is a CURATED set. Verified to exist in ChromaDB; re-run
#     verify_labels() (retrieval_eval.py) after any re-ingest.
#   - Expand from observed failures (use `--inspect` to pool/expand) — that's the point.
RETRIEVAL_QUERIES = [
    # ── REALISTIC (dept + min_level) ──────────────────────────────
    {"query": "machine learning",                   "departments": ["Computer Science"],                    "min_level": 3000, "relevant": ["CS3244"]},
    {"query": "data structures and algorithms",     "departments": ["Computer Science"],                    "min_level": 2000, "relevant": ["CS2040", "CS2040S", "CS3230"]},
    {"query": "natural language processing",        "departments": ["Computer Science"],                    "min_level": 4000, "relevant": ["CS4248"]},
    {"query": "computer vision",                    "departments": ["Computer Science"],                    "min_level": 4000, "relevant": ["CS4243"]},
    {"query": "artificial intelligence",            "departments": ["Computer Science"],                    "min_level": 3000, "relevant": ["CS3263", "CS5446"]},
    {"query": "computer security",                  "departments": ["Computer Science"],                    "min_level": 3000, "relevant": ["CS3235"]},
    {"query": "computer networks",                  "departments": ["Computer Science"],                    "min_level": 2000, "relevant": ["CS2105", "CS4226"]},
    {"query": "introductory programming",           "departments": ["Computer Science"],                    "min_level": 1000, "relevant": ["CS1101S", "CS2030", "CS2030S"]},
    {"query": "bioinformatics",                     "departments": ["Computer Science"],                    "min_level": 4000, "relevant": ["CS4220"]},
    {"query": "design and analysis of algorithms",  "departments": ["Computer Science"],                    "min_level": 3000, "relevant": ["CS3230"]},
    {"query": "probability and statistics",         "departments": ["Statistics and Data Science"],         "min_level": 2000, "relevant": ["ST2334"]},
    {"query": "introduction to data science",       "departments": ["Statistics and Data Science"],         "min_level": 1000, "relevant": ["DSA1101"]},
    {"query": "data analytics for business",        "departments": ["Information Systems and Analytics"],    "min_level": 4000, "relevant": ["BT4222", "IT5006"]},
    {"query": "quantitative methods for economics", "departments": ["Economics"],                           "min_level": 2000, "relevant": ["EC2104"]},
    {"query": "machine learning",                   "departments": ["Electrical and Computer Engineering"], "min_level": 2000, "relevant": ["EE2211", "EE2213"]},

    # ── HARD-PROBE (no filters — embedding-sensitivity test for step 2) ────
    {"query": "machine learning",                   "relevant": ["CS3244"]},
    {"query": "natural language processing",        "relevant": ["CS4248"]},
    {"query": "introductory programming",           "relevant": ["CS1101S", "CS2030", "CS2030S"]},
]
