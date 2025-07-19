import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# --- User authentication setup (simple demo, use a secure method for production) ---
USERS = {"admin": "admin123", "user": "user123"}
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None

def login_ui():
    st.title("Login to Aquaculture Dashboard")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if USERS.get(username) == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
        else:
            st.error("Incorrect username or password.")

def logout_ui():
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.experimental_rerun()

if not st.session_state["logged_in"]:
    login_ui()
    st.stop()
else:
    st.sidebar.write(f"Logged in as **{st.session_state['username']}**")
    logout_ui()

st.title("Aquaculture Supply Chain Finance & Traceability Dashboard")
st.write("Upload your supply chain datasets below or use the example datasets provided.")

# --- Example CSV text for easy download via st.download_button ---
example_transactions = """transaction_id,from_entity,to_entity,batch_id,transaction_date,delivery_date,payment_date,payment_term
1,Farmer A,Processor B,B001,2025-07-01,2025-07-03,2025-07-10,7
2,Processor B,Distributor C,B001,2025-07-05,2025-07-07,2025-07-15,8
3,Processor B,Distributor D,B002,2025-07-07,2025-07-09,2025-07-16,7
"""
example_batches = """batch_id,origin,production_date,status
B001,Farm X,2025-06-29,shipped
B002,Farm Y,2025-07-01,in transit
"""
example_logistics = """move_id,batch_id,from_location,to_location,start_date,end_date,logistics_cost
1,B001,Farm X,Processor B,2025-07-01,2025-07-03,200
2,B002,Farm Y,Processor B,2025-07-05,2025-07-07,250
"""

st.sidebar.markdown("#### Download Example Datasets")
st.sidebar.download_button("Download transactions.csv", example_transactions, "transactions.csv")
st.sidebar.download_button("Download batches.csv", example_batches, "batches.csv")
st.sidebar.download_button("Download logistics.csv", example_logistics, "logistics.csv")

# --- Data upload and fallback to example datasets ---
st.sidebar.markdown("#### Upload Your Data")
trans_file = st.sidebar.file_uploader("Upload transactions.csv", type='csv')
batch_file = st.sidebar.file_uploader("Upload batches.csv", type='csv')
log_file = st.sidebar.file_uploader("Upload logistics.csv", type='csv')

@st.cache_data
def load_csv(file, example):
    if file:
        return pd.read_csv(file)
    return pd.read_csv(pd.compat.StringIO(example))

transactions = load_csv(trans_file, example_transactions)
batches = load_csv(batch_file, example_batches)
logistics = load_csv(log_file, example_logistics)

# --- Core functions for analytics & network modelling ---
def build_graph(transactions, batches, logistics):
    G = nx.DiGraph()
    # Batch nodes
    for _, batch in batches.iterrows():
        G.add_node(batch['batch_id'], label='Batch', origin=batch['origin'])
    # Transaction edges
    for _, row in transactions.iterrows():
        G.add_node(row['from_entity'], label='Entity')
        G.add_node(row['to_entity'], label='Entity')
        G.add_edge(row['from_entity'], row['to_entity'], batch=row['batch_id'],
                   date=row['transaction_date'],
                   payment=row['payment_date'])
    # Logistics edges
    for _, row in logistics.iterrows():
        G.add_edge(row['from_location'], row['to_location'], batch=row['batch_id'],
                   start=row['start_date'], end=row['end_date'])
    return G

def payment_lead_times(transactions):
    return (pd.to_datetime(transactions['payment_date']) - pd.to_datetime(transactions['delivery_date'])).dt.days

def working_capital_cycle(transactions):
    return (pd.to_datetime(transactions['payment_date']) - pd.to_datetime(transactions['transaction_date'])).dt.days.mean()

def detect_bottlenecks(logistics):
    total_time = (pd.to_datetime(logistics['end_date']) - pd.to_datetime(logistics['start_date'])).dt.days
    avg = total_time.mean()
    return logistics[total_time > avg * 1.5]

def plot_graph(G):
    pos = nx.spring_layout(G, seed=42)
    edge_x, edge_y, edge_text = [], [], []
    for u, v, d in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        edge_text.append(f"{u} → {v}, batch {d.get('batch', '')}")

    node_x, node_y, node_text = [], [], []
    for node in G.nodes:
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(node))

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode='lines', line=dict(width=1, color='gray'),
        hoverinfo='text', showlegend=False
    )
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=node_text,
        marker=dict(size=20, color='LightSkyBlue'), textposition="bottom center",
        hoverinfo='text'
    )
    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20),
                      title="Supply Chain Network Map",
                      showlegend=False)
    return fig

# --- Dashboard Layout & Analytics ---
st.header("1. Network Visualization")
G = build_graph(transactions, batches, logistics)
fig = plot_graph(G)
st.plotly_chart(fig, use_container_width=True)

st.header("2. Key Metrics")
lead_times = payment_lead_times(transactions)
st.metric("Average Payment Lead Time (days)", f"{lead_times.mean():.1f}")
st.metric("Working Capital Cycle (days)", f"{working_capital_cycle(transactions):.1f}")

st.header("3. Bottlenecks")
bottlenecks = detect_bottlenecks(logistics)
if not bottlenecks.empty:
    st.write("Detected Bottlenecks in Logistics:")
    st.dataframe(bottlenecks)
else:
    st.write("No significant bottlenecks detected.")

st.header("4. Uploaded Data Previews")
with st.expander("Transactions Data"):
    st.dataframe(transactions)
with st.expander("Batches Data"):
    st.dataframe(batches)
with st.expander("Logistics Data"):
    st.dataframe(logistics)

st.success("Dashboard ready. Use the sidebar for login, data upload, and downloading templates.")
