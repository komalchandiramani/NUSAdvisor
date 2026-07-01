import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.tracing import setup_phoenix
setup_phoenix()

import ast
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from phoenix.client import Client
import pandas as pd
from chat import chat_with_log, chat_multi_turn
from evals.dataset import EVAL_QUESTIONS, STAY_ON_TOPIC_CASES
from evals.evaluators import (tool_calling_eval, course_exists_eval, search_relevance_eval, 
                              call_efficiency_eval, courses_state_eval, stay_on_topic)
client = Client()

def run_task(input) -> dict:
    messages = input.get("messages")
    if isinstance(messages, str):
        try:
            messages = ast.literal_eval(messages)
        except Exception:
            messages = None
    fn = lambda: chat_multi_turn(messages) if isinstance(messages, list) else chat_with_log(input["question"])
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=120)
        except FuturesTimeout:
            print(f"⚠️  Task timed out: {input.get('question') or input.get('messages')}")
            return None
        

dataset = client.datasets.create_dataset(
    name=f"nusadvisor-test-v4",
    dataframe=pd.DataFrame(EVAL_QUESTIONS),
    input_keys=["question", "messages", "expected_tools", 
                "expected_courses_taken", "expected_courses_planned"],
    output_keys=[]
)

client.experiments.run_experiment(
    dataset=dataset,
    task=run_task,
    evaluators=[tool_calling_eval, course_exists_eval, search_relevance_eval, 
                call_efficiency_eval, courses_state_eval],
    experiment_name="agent-quality-before-guardrails",
    experiment_description="Evaluates the basic quality of the agent."
)

guardrail_dataset = client.datasets.create_dataset(
    name=f"nusadvisor-guardrail-v1",
    dataframe=pd.DataFrame(STAY_ON_TOPIC_CASES),
    input_keys=["question", "messages", "category", "scope", "expected"],
    output_keys=[]
)
client.experiments.run_experiment(
    dataset=guardrail_dataset, 
    task=run_task,
    evaluators=[stay_on_topic],
    experiment_name="scope-guardrail-before-guardrails",
    experiment_description="Added more difficult test cases"
)

