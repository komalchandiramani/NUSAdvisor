import phoenix as px
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

def setup_phoenix(project_name: str = "nusadvisor"):
    # session = px.launch_app()
    tracer_provider = register(
        project_name=project_name,
        endpoint="http://localhost:6006/v1/traces"
    )
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    # return session