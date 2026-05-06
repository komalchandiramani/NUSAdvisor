import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.tracing import setup_phoenix
setup_phoenix()


from phoenix.client import Client
import pandas as pd
from chat import chat_with_log
from evals.dataset import EVAL_QUESTIONS
from evals.evaluators import tool_calling_eval, course_exists_eval, search_relevance_eval, call_efficiency_eval
import time

client = Client()

df = pd.DataFrame(EVAL_QUESTIONS)

dataset = client.datasets.create_dataset(
    name=f"nusadvisor-test-v1",
    dataframe=df,
    input_keys=["question", "expected_tools"],
    output_keys=[]
)

def run_task(input) -> dict:
    return chat_with_log(input["question"])


experiment = client.experiments.run_experiment(
    dataset=dataset,
    task=run_task,
    evaluators=[tool_calling_eval, course_exists_eval, search_relevance_eval, call_efficiency_eval]
)

