import streamlit as st
import pandas as pd
import hashlib
import os
import networkx as nx
import plotly.graph_objects as go

# ----------- Visually Appealing Background Styling ------------
def set_bg():
    st.markdown(
        """
        <style>
        .stApp {
            background-image: url('https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1920&q=80');
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        .block-container {
            background: rgba(255, 255, 255, 0.88);
            padding: 2rem 2.5rem 2.5rem 2.5rem;
            border-radius: 18px;
            box-shadow: 0 8px 32px 0 rgba(31,38,135,0.37);
        }
        </style>
        """, unsafe_allow_html=True
    )

set_bg()

# ------------ User Credential Utilities -----------------------
USERS_CSV = 'users.csv'

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_CSV):
        return pd.DataFrame(columns=['username', 'password'])
    return pd.read_csv(USERS_CSV)

def save_user(username, password):
    users = load_users()
    if username in users['username'].values:
        return False
    new_row = pd.DataFrame([{'username': username, 'password': hash_pw(password)}])
    users = pd.concat([users, new_row], ignore_index=True)
    users.to_csv(USERS_CSV, index=False)
    return True

def validate_login(username, password):
    users = load_users()
    match = users[(users['username'] == username) & (users['password'] == hash_pw(password))]
    return not match.empty

# ----------------- Session State Setups -----------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "registration_mode" not in st.session_state:
    st.session_state["registration_mode"] = False

# -------------------- Authentication Pages --------------------
def registration_page():
    st.title("Register New Account")
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")
    password2 = st.text_input("Confirm Password", type="password")
    if st.button("Create Account"):
        if not username or not password:
            st.error("Please complete all fields.")
        elif password != password2:
            st.error("Passwords do not match.")
        elif save_user(username, password):
            st.success("Registration successful! Please log in below.")
            st.session_state["registration_mode"] = False
        else:
            st.error("That username is already taken.")
    if st.button("Return to Login"):
        st.session_state["registration_mode"] = False

def login_page():
    st.title("Login to Aquaculture Dashboard")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    log, reg = st.columns([1,1])
    if log.button("Login"):
        if validate_login(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
        else:
            st.error("Incorrect username or password.")
    if reg.button("Register New Account"):
        st.session_state["registration_mode"] = True

def logout():
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.experimental_rerun()

# ------------- App Flow Management: Auth and Main -------------
if not st.session_state["logged_in"]:
    if st.session_state["registration_mode"]:
        registration_page()
    else:
        login_page()
    st.stop()
else:
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    logout()

# ---------------------------- Dashboard ------------------------
st.title("Aquaculture Supply Chain Finance & Traceability Dashboard")
st.markdown(
    "Upload your aquaculture supply chain datasets below. "
    "Visualizations and analytics will refresh with your uploads."
)

# --------------------- Sidebar: Only Upload -------------------
st.sidebar.markdown("### Upload Your Data")
trans_file = st.sidebar.file_uploader("Upload transactions.csv", type='csv')
batch_file = st.sidebar.file_uploader("Upload batches.csv", type='csv')
log_file = st.sidebar.file_uploader("Upload logistics.csv", type='csv')

@st.cache_data
def load_csv(file):
    if file:
        return pd.read_csv(file)
    else:
        st.warning("Please upload required CSV files to continue.")
        return pd.DataFrame()  # Return empty DataFrame for missing file

transactions = load_csv(trans_file)
batches = load_csv(batch_file)
logistics = load_csv(log_file)

# Only display dashboard if dataframes are not empty
if transactions.empty or batches.empty or logistics.empty:
    st.warning("Please upload all three required files: transactions.csv, batches.csv, and logistics.csv.")
    st.stop()

# --------------- Supply Chain Analysis and Visualization -----------------
def build_graph(transactions, batches, logistics):
    G = nx.DiGraph()
    for _, batch in batches.iterrows():
        G.add_node(batch['batch_id'], label='Batch', origin=batch['origin'])
    for _, row in transactions.iterrows():
        G.add_node(row['from_entity'], label='Entity')
        G.add_node(row['to_entity'], label='Entity')
        G.add_edge(row['from_entity'], row['to_entity'], batch=row['batch_id'],
                   date=row['transaction_date'],
                   payment=row['payment_date'])
    for _, row in logistics.iterrows():
        G.add_edge(row['from_location'], row['to_location'], batch=row['batch_id'],
                   start=row['start_date'], end=row['end_date'])
    return G

def payment_lead_times(trans):
    if 'payment_date' in trans and 'delivery_date' in trans:
        return (pd.to_datetime(trans['payment_date']) - pd.to_datetime(trans['delivery_date'])).dt.days
    return pd.Series([None]*len(trans))

def working_capital_cycle(trans):
    if 'payment_date' in trans and 'transaction_date' in trans:
        return (pd.to_datetime(trans['payment_date']) - pd.to_datetime(trans['transaction_date'])).dt.days.mean()
    return float('nan')

def detect_bottlenecks(logistics):
    if 'end_date' in logistics and 'start_date' in logistics:
        total_time = (pd.to_datetime(logistics['end_date']) - pd.to_datetime(logistics['start_date'])).dt.days
        if not len(total_time):
            return pd.DataFrame()
        avg = total_time.mean()
        return logistics[total_time > avg * 1.5]
    return pd.DataFrame()

def plot_graph(G):
    pos = nx.spring_layout(G, seed=42)
    edge_x, edge_y, edge_text = [], [], []
    for u, v, d in G.edges(data=True):
        x0, y0 = pos.get(u, (0,0))
        x1, y1 = pos.get(v, (0,0))
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        batch_label = f", batch {d.get('batch', '')}" if d.get('batch') else ""
        edge_text.append(f"{u} → {v}{batch_label}")

    node_x, node_y, node_text = [], [], []
    for node in G.nodes:
        x, y = pos.get(node, (0,0))
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(node))

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode='lines', line=dict(width=1, color='gray'),
        hoverinfo='text', showlegend=False
    )
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=node_text,
        marker=dict(size=20, color='LightSkyBlue', line=dict(width=2, color='darkblue')),
        textposition="bottom center",
        hoverinfo='text'
    )
    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        height=520, 
        margin=dict(l=24, r=24, t=60, b=32),
        title="Supply Chain Network Map",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Open Sans, Arial", size=15)
    )
    return fig

# ---------------------- Main Dashboard Sections ---------------------
st.header("1. Network Visualization")
G = build_graph(transactions, batches, logistics)
if len(G):
    fig = plot_graph(G)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Insufficient data provided for network visualization.")

st.header("2. Key Metrics")
lead_times = payment_lead_times(transactions)
working_cap = working_capital_cycle(transactions)
st.metric("Average Payment Lead Time (days)", f"{lead_times.mean():.1f}" if lead_times.notnull().any() else "-")
st.metric("Working Capital Cycle (days)", f"{working_cap:.1f}" if not pd.isna(working_cap) else "-")

st.header("3. Bottlenecks")
bottlenecks = detect_bottlenecks(logistics)
if bottlenecks is not None and not bottlenecks.empty:
    st.warning("Detected Bottlenecks in Logistics:")
    st.dataframe(bottlenecks)
else:
    st.success("No significant bottlenecks detected.")

st.header("4. Uploaded Data Previews")
with st.expander("Transactions Data"):
    st.dataframe(transactions)
with st.expander("Batches Data"):
    st.dataframe(batches)
with st.expander("Logistics Data"):
    st.dataframe(logistics)

st.success("Dashboard ready. Use the sidebar for registration, login, and uploading your supply chain data files.")
