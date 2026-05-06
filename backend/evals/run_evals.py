import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.tracing import setup_phoenix
setup_phoenix()


from phoenix.client import Client
import pandas as pd
from chat import chat_with_log, chat_multi_turn
from evals.dataset import EVAL_QUESTIONS
from evals.evaluators import tool_calling_eval, course_exists_eval, search_relevance_eval, call_efficiency_eval, courses_state_eval

client = Client()

df = pd.DataFrame(EVAL_QUESTIONS)

dataset = client.datasets.create_dataset(
    name=f"nusadvisor-test-v3",
    dataframe=df,
    input_keys=["question", "messages", "expected_tools", "expected_courses_taken", "expected_courses_planned"],
    output_keys=[]
)


def run_task(input) -> dict:
    import ast
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
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


experiment = client.experiments.run_experiment(
    dataset=dataset,
    task=run_task,
    evaluators=[tool_calling_eval, course_exists_eval, search_relevance_eval, call_efficiency_eval, courses_state_eval]
)

