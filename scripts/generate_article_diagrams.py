import os
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path

def setup_plot(figsize=(8, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')
    plt.subplots_adjust(left=0.05, right=0.95, top=0.85, bottom=0.05)
    return fig, ax

def save_plot(fig, filename):
    out_dir = Path("article/assets")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / filename, facecolor='#ffffff', edgecolor='none', bbox_inches='tight', pad_inches=0.1, dpi=300)
    plt.close(fig)

def draw_state_machine():
    fig, ax = setup_plot((20, 8))
    
    G = nx.DiGraph()
    states = ["draft", "preflight", "ready_for_takeoff", "in_flight", "rth", "landed", "postflight", "completed"]
    for s in states:
        G.add_node(s)
        
    G.add_edges_from([
        ("draft", "preflight"),
        ("preflight", "ready_for_takeoff"),
        ("ready_for_takeoff", "in_flight"),
        ("in_flight", "rth"),
        ("in_flight", "landed"),
        ("rth", "landed"),
        ("landed", "postflight"),
        ("postflight", "completed")
    ])
    
    pos = {
        "draft": (0, 0),
        "preflight": (3, 0),
        "ready_for_takeoff": (7, 0),
        "in_flight": (11, 0),
        "rth": (14.5, 1.5),
        "landed": (14.5, -1.5),
        "postflight": (18, 0),
        "completed": (21, 0)
    }
    
    node_colors = ['#16A34A' if s == 'completed' else '#E0F2FE' for s in states]
    edge_colors = ['#102033' if s == 'completed' else '#0369A1' for s in states]
    labels = {s: s.replace('_', '\n').upper() for s in states}
    
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=18000, edgecolors=edge_colors, linewidths=3)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#475569', arrows=True, arrowsize=30, connectionstyle="arc3,rad=0.1", width=2)
    nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=20, font_color='#0f172a', font_weight='bold')
    
    ax.margins(0.15)
    ax.set_title("MissionSupervisor State Machine", color='#0f172a', pad=25, fontsize=28, fontweight='bold')
    ax.axis('off')
    save_plot(fig, "supervisor_state_machine.png")

def draw_fipa_flow():
    fig, ax = setup_plot((16, 12))
    
    agents = ["Telemetry\nAnalyst", "Meteorology\nAgent", "Mission\nSupervisor", "Safety\nOfficer", "Report\nWriter"]
    pos = {
        agents[0]: (2, 7),
        agents[1]: (2, 3),
        agents[2]: (6, 5),
        agents[3]: (10, 7),
        agents[4]: (10, 3)
    }
    
    G = nx.DiGraph()
    for a in agents: G.add_node(a)
    
    G.add_edge(agents[0], agents[2], label="INFORM\n(GPS/Route)")
    G.add_edge(agents[1], agents[2], label="PROPOSE\n(High Wind)")
    G.add_edge(agents[2], agents[3], label="REQUEST\n(Emergency Eval)")
    G.add_edge(agents[3], agents[2], label="INFORM\n(Land Now)")
    G.add_edge(agents[2], agents[4], label="REQUEST\n(Postflight Report)")
    
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color='#F1F5F9', node_size=24000, edgecolors='#F97316', linewidths=4)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#64748B', arrows=True, arrowsize=35, min_source_margin=75, min_target_margin=75, width=3)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=22, font_color='#0f172a', font_weight='bold')
    
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_color='#047857', font_size=18, bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="none", alpha=0.9))
    
    ax.margins(0.2)
    ax.set_title("FIPA-ACL Agent Communication Flow", color='#0f172a', pad=25, fontsize=28, fontweight='bold')
    ax.axis('off')
    save_plot(fig, "fipa_communication_flow.png")

def draw_mas_architecture():
    fig, ax = setup_plot((16, 12))
    
    boxes = {
        "Flask App\nWeb UI": (2, 8),
        "MissionStore\n(SQLite)": (2, 4),
        "Mission\nSupervisor": (6, 6),
        "Safety\nOfficer": (10, 9),
        "Telemetry\nAnalyst": (10, 7.5),
        "Meteorology\nAgent": (10, 4.5),
        "Report\nWriter": (10, 3),
    }
    
    G = nx.DiGraph()
    for b in boxes: G.add_node(b)
    
    edges = [
        ("Flask App\nWeb UI", "Mission\nSupervisor"),
        ("Mission\nSupervisor", "MissionStore\n(SQLite)"),
        ("Mission\nSupervisor", "Safety\nOfficer"),
        ("Mission\nSupervisor", "Telemetry\nAnalyst"),
        ("Mission\nSupervisor", "Meteorology\nAgent"),
        ("Mission\nSupervisor", "Report\nWriter"),
        ("MissionStore\n(SQLite)", "Mission\nSupervisor")
    ]
    G.add_edges_from(edges)
    
    nx.draw_networkx_nodes(G, boxes, ax=ax, node_size=26000, node_shape='s', node_color='#F8FAFC', edgecolors='#7C3AED', linewidths=4)
    nx.draw_networkx_labels(G, boxes, ax=ax, font_size=22, font_color='#0f172a', font_weight='bold')
    nx.draw_networkx_edges(G, boxes, ax=ax, edge_color='#64748B', arrows=True, arrowsize=35, width=3)
    
    ax.margins(0.15)
    ax.set_title("UAV Multi-Agent Edge Architecture", color='#0f172a', pad=25, fontsize=28, fontweight='bold')
    ax.axis('off')
    save_plot(fig, "mas_architecture.png")

if __name__ == "__main__":
    draw_state_machine()
    draw_fipa_flow()
    draw_mas_architecture()
    print("Diagrams generated successfully with compact layout and safety margins in article/assets/")
