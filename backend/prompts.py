RELEVANCE_PROMPT = """
A student asked: {question}

The agentic NUSAdvisor responded with this:
{response}

Is the answer relevant to what the student was asking about?
A relevant result directly relates to the topic or goal in the question.
Any courses mentioned must be relevant to the question.
An irrelevant result is off-topic or unrelated to the student's intent.

EXPLANATION: [your reasoning]
LABEL: "relevant" or "irrelevant"
"""

### -------------------------------------------------------------------------------------

SYS_PROMPT = """You are a smart NUS course advisor. Use the search_modules_tool to look up available courses.
You are allowed to make multiple calls (either together or in sequence).
Only look up information when you are sure of what you want.
If you need to look up some information before asking a follow up question, you are allowed to do that!
When a student mentions a specific course code, use get_module_tool for a direct lookup instead of search_modules_tool.
When a student tells you they have taken or are planning to take a course, record it immediately — do not search for the course first.

Course levels at NUS:
- Undergraduate: 1000-4000 level (sometimes 5000)
- Master's: 5000-6000 level (mostly 5000)
- PhD: 5000-6000 level

When listing course codes from prerequisite descriptions, copy them exactly as returned by the tool. Do not truncate or modify course codes.
NUS module codes follow this format: 2-4 uppercase letters followed by 4 digits, 
optionally followed by a 1-3 uppercase letters (e.g. CS3244, FIN3703A, MA1521, ACC1701XA, DMB1201ACC).


When recommending courses from the student's planned list, check that prerequisites are satisfied by their completed courses. Flag any unmet prerequisites clearly.
When the student has multiple planned courses, suggest a sensible order to take them based on prerequisites and course level.
"""

### -------------------------------------------------------------------------------------

EXTRACT_CODES_PROMPT = """
Extract all NUS module codes mentioned in the following text.
NUS module codes follow this format: 2-4 uppercase letters followed by 4 digits, 
optionally followed by a 1-3 uppercase letters (e.g. CS3244, FIN3703A, MA1521, ACC1701XA, DMB1201ACC).

If a module is written as "FIN3703 (A/B/C)", extract each variant separately: FIN3703A, FIN3703B, FIN3703C.
If a module is written as "FIN3701 (A/B)", extract: FIN3701A, FIN3701B.
If a module is written as "CS3244", extract: CS3244.

Return only a JSON array of module codes, nothing else. Example: ["CS3244", "FIN3703A", "MA1521"]
If no module codes are found, return: []

Text:
{text}
"""

### -------------------------------------------------------------------------------------

TITLE_PROMPT = """Summarize the following message as a short chat title in 5 words or less.
Return only the title, no punctuation or quotes.

Message: {message}
"""

### -------------------------------------------------------------------------------------