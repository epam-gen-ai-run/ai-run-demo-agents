from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langgraph.graph import StateGraph, END

from typing import TypedDict, List

from common.utils.chat_model_factory import create_chat_model

from dotenv import load_dotenv

load_dotenv()

class State(TypedDict):
    text: str
    classification: str
    entities: List[str]
    summary: str

class ResearchState(TypedDict):
    user_query: str
    research_topic: str
    research_findings: str
    research_report_title: str
    research_report: str

llm = create_chat_model()

def research_topic_extraction_node(state: ResearchState) -> State:
    prompt = PromptTemplate(
        input_variables=["user_query"],
        template="""
        Extract the topic to conduct a research from the following query:
        {user_query}
        
        Topic:
        """
    )
    message = HumanMessage(content=prompt.format(user_query=state["user_query"]))
    
    research_topic = llm.invoke([message]).content.strip()
    
    return {"research_topic": research_topic}

def researcher_node(state: ResearchState) -> State:
    prompt = PromptTemplate.from_template(
        """
        You are an experienced research specialist for {research_topic} with a talent for finding relevant information from various sources.
        You excel at organizing information in a clear and structured manner, making complex topics accessible to others.
        
        Your goal:
        Find comprehensive and accurate information about {research_topic} with a focus on recent developments and key insights.
        
        Your task:
        Conduct thorough research on {research_topic}. Focus on:
            1. Key concepts and definitions
            2. Historical development and recent trends
            3. Major challenges and opportunities
            4. Notable applications or case studies
            5. Future outlook and potential developments
        Make sure to organize your findings in a structured format with clear sections.
        
        Expected output:
        A comprehensive research document with well-organized sections covering all the requested aspects of {research_topic}.
        Include specific facts, figures, and examples where relevant.
        
        Your research findings:
        """
    )
    chain = prompt | llm
    
    response = chain.invoke({"research_topic": state["research_topic"]})
    
    return {"research_findings": response.content}

def analyst_node(state: ResearchState) -> State:
    prompt = PromptTemplate.from_template(
        """
        You are a skilled data analyst and report writer for {research_topic} with a background in data interpretation and technical writing.
        You have a talent for identifying patterns and extracting meaningful insights from research data,
        then communicating those insights effectively through well-crafted reports.
        
        Your task:
        Analyze research findings and create a comprehensive, well-structured report on {research_topic} that presents insights in a clear and engaging way.
        The report should:
            1. Be titled
            2. Begin with an executive summary
            3. Include all key information from the research
            4. Provide insightful analysis of trends and patterns
            5. Offer recommendations or future considerations
            6. Be formatted in a professional, easy-to-read style with clear headings
        
        Research findings to analyze:
        {research_findings}
        
        Provide your response in valid JSON format following the structure below.
        {{
            "title": "string - The report title",
            "content": "string - The report content"
        }}
        """
    )
    chain = prompt | llm.with_structured_output(method="json_mode")
    
    response = chain.invoke({
        "research_topic": state["research_topic"],
        "research_findings": state["research_findings"]
    })
    
    return {
        "research_report_title": response["title"],
        "research_report": response["content"]
    }

workflow = StateGraph(ResearchState)
workflow.add_node("node_research_topic_extraction", research_topic_extraction_node)
workflow.add_node("node_researcher", researcher_node)
workflow.add_node("node_analyst", analyst_node)

workflow.set_entry_point("node_research_topic_extraction")
workflow.add_edge("node_research_topic_extraction", "node_researcher")
workflow.add_edge("node_researcher", "node_analyst")
workflow.add_edge("node_analyst", END)

app = workflow.compile()

if __name__ == "__main__":
    state_input = {"user_query": "What is the most important thing to do to fix the planet?"}
    
    result = app.invoke(state_input)
    
    print(">>> Research Topic:", result["research_topic"])
    print(">>> Research Findings:", result["research_findings"])
    print(">>> Research Report Title:", result["research_report_title"])
    print(">>> Research Report:", result["research_report"]) 