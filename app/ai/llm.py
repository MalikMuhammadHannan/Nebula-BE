from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


model = ChatOllama(
    model="qwen2.5:0.5b",
    temperature=0.2,
    num_predict=400,
    repeat_penalty=1.3,
)

# repeat_penalty breaks Ollama's tool-calling for qwen2.5:0.5b (it discourages
# the repeated structural tokens a function call needs), so tool-calling
# callers get a separate, penalty-free model instance.
tool_model = ChatOllama(
    model="qwen2.5:0.5b",
    temperature=0.2,
    num_predict=400,
)


class LLMService:
    @staticmethod
    def get_model():
        return model

    @staticmethod
    def get_tool_model():
        return tool_model

    @staticmethod
    def get_prompt(text: str):
        return ChatPromptTemplate.from_template(text)
