import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.tracing import setup_phoenix
setup_phoenix()

from phoenix.client import Client
from evals.evaluators import tool_calling_eval, course_exists_eval, search_relevance_eval, call_efficiency_eval, courses_state_eval

EXPERIMENT_ID = "RXhwZXJpbWVudDoxMw=="  # update this each time

client = Client()
experiment = client.experiments.get_experiment(experiment_id=EXPERIMENT_ID)
client.experiments.evaluate_experiment(
    experiment=experiment,
    evaluators=[tool_calling_eval, course_exists_eval, search_relevance_eval, call_efficiency_eval, courses_state_eval]
)