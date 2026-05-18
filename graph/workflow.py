import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from schema.state import PRReviewState
from agents.diff_analyzer import diff_analyzer
from agents.bug_detector import bug_detector
from agents.style_reviewer import style_reviewer
from agents.judge import judge

def build_graph():
    workflow = StateGraph(PRReviewState)
    
    # Nodes
    workflow.add_node("diff_analyzer", diff_analyzer)
    workflow.add_node("bug_detector", bug_detector)
    workflow.add_node("style_reviewer", style_reviewer)
    workflow.add_node("judge", judge)
    
    # Edges
    workflow.set_entry_point("diff_analyzer")
    workflow.add_edge("diff_analyzer", "bug_detector")
    workflow.add_edge("bug_detector", "style_reviewer")
    workflow.add_edge("style_reviewer", "judge")
    workflow.add_edge("judge", END)
    
    # SQLite checkpointing
    conn = sqlite3.connect("checkpoint.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return workflow.compile(checkpointer=checkpointer)
        
graph = build_graph()