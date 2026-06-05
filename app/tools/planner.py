from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.db import get_vector_store
from app.core.config import settings

@tool
def suggest_paper_titles(topic: str, num_titles: int = 5, feedback: str = None) -> str:
    """
    Suggests academic paper titles based on a topic and relevant documents in the database.
    """
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(topic, k=5)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.7)
    
    system_prompt = "You are a senior academic researcher. Suggest original and catchy paper titles based on the provided context."
    if feedback:
        system_prompt += f" Consider this user feedback: {feedback}"
        
    user_prompt = f"Topic: {topic}\n\nContext from similar papers:\n{context}\n\nPlease suggest {num_titles} titles."
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return response.content

@tool
def generate_paper_outline(topic: str, title: str, feedback: str = None) -> str:
    """
    Generates a structured hierarchical outline for a paper based on a topic and title.
    """
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(f"{topic} {title}", k=5)
    context = "\n\n".join([doc.page_content for doc in docs])

    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.3)

    system_prompt = "You are an expert academic planner. Generate a detailed, hierarchical outline (Introduction, Literature Review, Methodology, etc.) for a paper."
    if feedback:
        system_prompt += f" Take this feedback into account: {feedback}"

    user_prompt = f"Topic: {topic}\nTitle: {title}\n\nContext:\n{context}\n\nGenerate a structured outline."

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    return response.content


@tool
def plan_paper_sections(outline: str) -> str:
    """
    Parses a paper outline into a clean, ordered list of top-level section titles.

    Use this immediately AFTER generating an outline and BEFORE writing the full
    paper. It returns a deterministic, numbered list of the sections to draft, in
    order, so every section is covered exactly once. Iterate this list and call
    `draft_paper_section` for each title in turn.

    Args:
        outline: The full paper outline (e.g. from generate_paper_outline).
    """
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)

    system_prompt = (
        "You are an academic editor. Extract ONLY the top-level section titles "
        "from the given paper outline, in their original order. Ignore "
        "sub-sections and bullet points. Return them as a numbered list, one "
        "section title per line, with no extra commentary.\n\n"
        "Example:\n1. Introduction\n2. Related Work\n3. Methodology\n4. Results\n"
        "5. Discussion\n6. Conclusion"
    )
    user_prompt = f"Outline:\n{outline}\n\nList the top-level section titles in order."

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    return response.content
