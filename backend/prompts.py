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

Course levels at NUS:
- Undergraduate: 1000-4000 level (sometimes 5000)
- Master's: 5000-6000 level (mostly 5000)
- PhD: 5000-6000 level
"""

### -------------------------------------------------------------------------------------

EXTRACT_CODES_PROMPT = """
Extract all NUS module codes mentioned in the following text.
NUS module codes follow this format: 2-4 uppercase letters followed by 4 digits, 
optionally followed by a single uppercase letter (e.g. CS3244, FIN3703A, MA1521).

If a module is written as "FIN3703 (A/B/C)", extract each variant separately: FIN3703A, FIN3703B, FIN3703C.
If a module is written as "FIN3701 (A/B)", extract: FIN3701A, FIN3701B.
If a module is written as "CS3244", extract: CS3244.

Return only a JSON array of module codes, nothing else. Example: ["CS3244", "FIN3703A", "MA1521"]
If no module codes are found, return: []

Text:
{text}
"""

### -------------------------------------------------------------------------------------