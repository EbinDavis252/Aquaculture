import streamlit as st
import pandas as pd
import hashlib
import os
import networkx as nx
import plotly.graph_objects as go

# --------- Stylish Background -----------
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

# ---------- User Credential Utilities ------------
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

# ------------ Session State Setups ------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "registration_mode" not in st.session_state:
    st.session_state["registration_mode"] = False

# ------------- Authentication Pages -------------
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

# ----------------- App Authentication Flow -----------------
if not st.session_state["logged_in"]:
    if st.session_state["registration_mode"]:
        registration_page()
    else:
        login_page()
    st.stop()
else:
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    logout()

# --------- Sidebar File Upload (Before Dashboard) -----------
uploaded_file = st.sidebar.file_uploader(
    "Upload your supply chain CSV (with columns for transactions, batches, logistics, etc.)",
    type='csv'
)

# ------------ Main Dashboard Logic --------------------------
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.title("Aquaculture Supply Chain Finance & Traceability Dashboard")
        st.markdown(
            "Uploaded aquaculture supply chain CSV file preview. "
            "Below are analytics and visualizations from your data."
        )

        st.header("Data Preview")
        st.dataframe(df)

        # Example: Visualize as a network graph using assumed columns
        def build_graph(df):
            G = nx.DiGraph()
            if {'from_entity','to_entity','batch_id'}.issubset(df.columns):
                for _, row in df.iterrows():
                    G.add_node(row['from_entity'], label='Entity')
                    G.add_node(row['to_entity'], label='Entity')
                    G.add_node(row['batch_id'], label='Batch')
                    G.add_edge(row['from_entity'], row['to_entity'], batch=row['batch_id'])
            return G

        G = build_graph(df)

        def plot_graph(G):
            pos = nx.spring_layout(G, seed=42)
            edge_x, edge_y = [], []
            for u, v in G.edges():
                x0, y0 = pos.get(u, (0,0))
                x1, y1 = pos.get(v, (0,0))
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]
            node_x, node_y, node_text = [], [], []
            for node in G.nodes:
                x, y = pos.get(node, (0,0))
                node_x.append(x)
                node_y.append(y)
                node_text.append(str(node))
            edge_trace = go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(width=1, color='gray'),
                                    hoverinfo='none', showlegend=False)
            node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text,
                                    marker=dict(size=20, color='LightSkyBlue', line=dict(width=2, color='darkblue')),
                                    textposition="bottom center", hoverinfo='text')
            fig = go.Figure([edge_trace, node_trace])
            fig.update_layout(
                height=500, margin=dict(l=24, r=24, t=60, b=32),
                title="Supply Chain Network Map",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Open Sans, Arial", size=15)
            )
            return fig

        if len(G):
            st.header("Network Visualization")
            fig = plot_graph(G)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Insufficient data provided for network visualization (needs 'from_entity', 'to_entity', 'batch_id').")

        # Key Metrics: Payment Lead Time and Working Capital Cycle
        if {'payment_date','delivery_date','transaction_date'}.issubset(df.columns):
            lead_times = (pd.to_datetime(df['payment_date']) - pd.to_datetime(df['delivery_date'])).dt.days
            working_cap = (pd.to_datetime(df['payment_date']) - pd.to_datetime(df['transaction_date'])).dt.days.mean()
            st.metric("Average Payment Lead Time (days)", f"{lead_times.mean():.1f}")
            st.metric("Working Capital Cycle (days)", f"{working_cap:.1f}")
        else:
            st.info("Metrics unavailable: ensure your uploaded data has 'payment_date', 'delivery_date', 'transaction_date' columns.")

        # Bottleneck: Find overly long logistics steps
        if {'start_date','end_date'}.issubset(df.columns):
            total_time = (pd.to_datetime(df['end_date']) - pd.to_datetime(df['start_date'])).dt.days
            avg = total_time.mean()
            bottlenecks = df[total_time > avg * 1.5]
            st.header("Bottlenecks")
            if not bottlenecks.empty:
                st.warning("Detected Bottlenecks in Logistics:")
                st.dataframe(bottlenecks)
            else:
                st.success("No significant bottlenecks detected.")
        else:
            st.info("Bottleneck detection unavailable: ensure your uploaded data has 'start_date', 'end_date' columns.")

    except Exception as e:
        st.error(f"Error loading data: {e}")
else:
    st.title("Aquaculture Supply Chain Finance & Traceability Dashboard")
    st.info("Please upload your supply chain CSV file in the sidebar to get started.")
