from typing import TypedDict, Annotated, Sequence,Optional
import operator
from langgraph.types import Send

from langgraph.graph import END, START


from langchain_core.messages import BaseMessage, HumanMessage,ToolMessage,AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langchain_mistralai import ChatMistralAI
from langchain_perplexity import ChatPerplexity
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.runnable import RunnableConfig
import os
import time
import firestore

from langchain_core.messages import SystemMessage

from config import PPLX_API_KEY, GOOGLE_API_KEY,MISTRAL_API_KEY
from retriever import parse_links,retrieve_url

from langsmith import traceable

models = {
    
    "mistral": ChatMistralAI(
    model="codestral-latest",
    temperature=0.6,
    max_retries=2,
    endpoint='https://codestral.mistral.ai/v1',
    api_key = MISTRAL_API_KEY
), "gemini":
ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=GOOGLE_API_KEY
),
'perplexity': ChatPerplexity(
    model="sonar",
    temperature=0.7,
    api_key=PPLX_API_KEY
)
}
models['default'] = models['mistral']

# Define the state
class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    links: Annotated[Sequence[BaseMessage], operator.add]
    link_summary: Annotated[Sequence[BaseMessage], operator.add]
class ConfigSchema(TypedDict):
    model: Optional[str]
    system_message: Optional[str]


# Define the nodes
def initial_router(state: AgentState,config: RunnableConfig):
    messages = state['messages']
    links = parse_links(messages[-1].content)
    for link in links:
        state['links'] = state['links'] + [link]
    return [Send("link_summariser", {"link": link}) for link in state['links']]

@traceable(name="Note Summariser")
def note_summariser_model(state: AgentState,config: RunnableConfig):
    messages = state['messages']
    model_name = config["configurable"].get("note_summariser_model","default")
    model = models[model_name]
    if "summariser_message" in config["configurable"]:
        messages = messages + [HumanMessage(content=config["configurable"]["summariser_message"])] 
    if "link_summary" in state:
        for link_summary in state['link_summary']:
            messages = messages + [HumanMessage(content=link_summary)] 
    response = model.invoke(messages)
    return {"messages": [response]}


@traceable(name="Link Summariser")
def link_summariser_model(state: AgentState,config: RunnableConfig):
    model_name = config["configurable"].get("link_summariser_model","default")
    model = models[model_name]
    print(model)
    if  'link' in state and state['link'] is not None:
        try:
            link_text = retrieve_url(state['link'])
            response = model.invoke([HumanMessage(content="Please provide a short summary of the material on the following website: \n "+link_text)])
            return {"link_summary": [response.content]}
        except(Exception) as e:
            print(e)
            return {"link_summary": ["not available"]}
    else:
        return {"link_summary": ["not available"]}

@traceable(name="Tagger")
def tagger_model(state: AgentState,config: RunnableConfig):
    messages = state['messages']
    model_name = config["configurable"].get("tagger_model","default")
    model = models[model_name]
    if "tagger_message" in config["configurable"]:
        messages = messages + [HumanMessage(content=config["configurable"]["tagger_message"])] 
    response = model.invoke(messages)
    return {"messages": [response]}

# Build the graph
workflow = StateGraph(AgentState)

# Define the entry point

workflow.add_node("note_summariser", note_summariser_model)
workflow.add_node("link_summariser", link_summariser_model)
workflow.add_node("tag", tagger_model)
workflow.add_conditional_edges(START, initial_router)
workflow.add_edge('link_summariser', 'note_summariser')
workflow.add_edge('note_summariser', 'tag')

workflow.set_finish_point('tag')


# Compile the graph
app = workflow.compile()


def process_notes(source_path: str, destination_path: str, config: Optional[dict] = None):
    """
    Processes notes from a source using the agent and saves the transformed notes to a destination.
    """
    db = firestore.get_firestore_db()
    if not db:
        print("Failed to get Firestore database connection.")
        return
    notes = None
    notes = firestore.read_notes_from_firestore(db)
    

 # List to store all transformed notes
    transformed_notes_list = []

    for note in notes[20:]:
        initial_state = {"messages": [HumanMessage(content=note['content'][:1000000])]}  # Assuming 'content' is the key for note content
        print(initial_state)
        result = app.invoke(initial_state, config)

        # Extract content from the agent's result (assuming it's in a BaseMessage)
        transformed_content = result["messages"][-2].content if result and result.get("messages") and len(result["messages"]) >= 2 else ""
        tags = result["messages"][-1].content.split(',') if result and result.get("messages") and len(result["messages"]) >= 1 and isinstance(result["messages"][-1].content, str) else []

 # Create transformed note, copying existing fields and updating content/modification dates
        transformed_note = note.copy()
        transformed_note['content'] = transformed_content
        transformed_note['tags'] = tags
        transformed_note['modificationDate'] = transformed_note['modifydate'] = time.time()

        transformed_notes_list.append(transformed_note)

        firestore.save_note_to_firestore(db, transformed_note, destination_path)
    # Save all processed notes to the destination document after the loop
    # firestore.save_notes_to_firestore(db, transformed_notes_list, destination_path)
if __name__ == "__main__":
    config = {
    "configurable": {
        "note_summariser_model": "default", 
        "link_summariser_model": "gemini", 
        "tagger_model": "default",
        "summariser_message":"You are a summariser bot that should provide a short summary of the content of the note, also including the material retrieved from the following links if possible",
        "tagger_message":"You are a tagging bot that should review the above content, then add appropriate tags. You should return your response as a comma-delimited list. Do not use any spaces in your tags, though an underscore is okay. Do not use commas in your response, except for separating tags. Don't include any wrapping text - only the tags, please."
    }}
    # Example of fetching a single note (replace with logic to get the specific note you want to test)
    source = "simplenote_backup" # Assuming this is the document name in firestore.py
    destination = "simplenote_processed" # Assuming this is the document name in firestore.py

    print("Starting note processing...")
    process_notes(source, destination, config)
    print("Note processing finished.")