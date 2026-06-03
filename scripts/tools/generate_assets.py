import os
import matplotlib.pyplot as plt
import networkx as nx

os.makedirs('assets', exist_ok=True)

# 1. MAS Architecture Diagram
plt.figure(figsize=(10, 6), facecolor='#FAFAFA')
G = nx.DiGraph()

# Nodes
G.add_node("UI/Backend", pos=(0, 1))
G.add_node("Coordinator", pos=(1, 1))
G.add_node("Risk Assessor", pos=(2, 1.5))
G.add_node("Flight Advisor", pos=(2, 0.5))
G.add_node("Report Writer", pos=(3, 1))

# Edges
G.add_edge("UI/Backend", "Coordinator", label="Trigger")
G.add_edge("Coordinator", "Risk Assessor", label="REQUEST (FIPA)")
G.add_edge("Risk Assessor", "Coordinator", label="INFORM")
G.add_edge("Coordinator", "Flight Advisor", label="REQUEST")
G.add_edge("Flight Advisor", "Coordinator", label="PROPOSE")
G.add_edge("Coordinator", "Report Writer", label="REQUEST")
G.add_edge("Report Writer", "Coordinator", label="INFORM")
G.add_edge("Coordinator", "UI/Backend", label="Response")

pos = nx.get_node_attributes(G, 'pos')
labels = nx.get_edge_attributes(G, 'label')

nx.draw(G, pos, with_labels=True, node_size=4000, node_color='#00d4ff', font_size=10, font_weight='bold', font_color='#16213e', edge_color='#64748b', arrows=True, arrowsize=20)
nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=8)

plt.title('Multi-Agent System (MAS) & FIPA-ACL Architecture', fontsize=14)
plt.tight_layout()
plt.savefig('assets/mas_architecture.png', dpi=300)
plt.close()

# 2. Checklist Progress Chart (Dummy Data)
plt.figure(figsize=(8, 5), facecolor='#FAFAFA')
phases = ['Environment', 'Pre-Flight', 'In-Flight', 'Post-Flight']
completion = [100, 100, 80, 0]

plt.bar(phases, completion, color=['#4caf50', '#4caf50', '#ff9800', '#f44336'])
plt.ylim(0, 110)
plt.ylabel('Completion %')
plt.title('Autonomous Mission Phase Tracking')
for i, v in enumerate(completion):
    plt.text(i, v + 2, str(v) + '%', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig('assets/phase_progress.png', dpi=300)
plt.close()

print("Assets generated successfully in assets/ directory.")
