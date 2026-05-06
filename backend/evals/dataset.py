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
