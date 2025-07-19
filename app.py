import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import hashlib
import os
import networkx as nx
import plotly.graph_objects as go
import datetime

# --------- App Brand & Styling ----------
st.set_page_config(page_title="AquaChain Portal", layout="wide", page_icon="🐟")

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
            background: rgba(255,255,255,0.92);
            padding: 2rem 2.5rem 2.5rem 2.5rem;
            border-radius: 18px;
            box-shadow: 0 8px 32px 0 rgba(31,38,135,0.26);
        }
        </style>
        """, unsafe_allow_html=True
    )

set_bg()
st.markdown("<h1 style='color:#095561;font-size:2.3rem'>🐟 AquaChain Portal</h1>", unsafe_allow_html=True)
st.markdown("##### Secure, Real-time Aquaculture Supply Chain Dashboard")

# ---------- User Credential Utilities -----------
USERS_CSV = 'users.csv'
ELEVATED_ROLES = ['Admin', 'Manager', 'Supplier', 'Auditor']
REGISTRATION_ROLE = "User"

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_CSV):
        return pd.DataFrame(columns=['username', 'password', 'role'])
    return pd.read_csv(USERS_CSV)

def save_user(username, password, role):
    users = load_users()
    if username in users['username'].values:
        return False
    df_new = pd.DataFrame([{
        'username': username,
        'password': hash_pw(password),
        'role': role
    }])
    users = pd.concat([users, df_new], ignore_index=True)
    users.to_csv(USERS_CSV, index=False)
    return True

def validate_login(username, password):
    users = load_users()
    match = users[(users['username'] == username) & (users['password'] == hash_pw(password))]
    if not match.empty:
        return match.iloc[0]['role']
    return None

# --------- Session State Setups ----------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "registration_mode" not in st.session_state:
    st.session_state["registration_mode"] = False
if "onboarded" not in st.session_state:
    st.session_state["onboarded"] = False

# --------- Registration Page (Restricted Role) ----------
def registration_page():
    st.header("Register New Account")
    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")
    password2 = st.text_input("Confirm Password", type="password")
    role = REGISTRATION_ROLE  # Only "User" allowed for public registration
    st.markdown("You will be registered as a standard user. For elevated access, please contact an administrator.")
    if st.button("Create Account"):
        if not username or not password:
            st.error("Please complete all fields.")
        elif password != password2:
            st.error("Passwords do not match.")
        elif save_user(username, password, role):
            st.success("Registration successful! Please log in below.")
            st.session_state["registration_mode"] = False
        else:
            st.error("That username is already taken.")
    if st.button("Return to Login"):
        st.session_state["registration_mode"] = False

def login_page():
    st.header("Login to AquaChain")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns([1,1])
    if col1.button("Login"):
        role = validate_login(username, password)
        if role:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
            st.experimental_rerun()
        else:
            st.error("Incorrect username or password.")
    if col2.button("Register New Account"):
        st.session_state["registration_mode"] = True

def logout():
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["role"] = None
        st.experimental_rerun()

# --------- Admin-only: Manage Users & Elevate Roles ----------
def admin_manage_users():
    st.subheader("User Management (Admin only)")
    users = load_users()
    st.dataframe(users)
    st.info("To assign roles beyond User, contact technical admin to update the user database.")

# --------- Main App Workflow (with Corrected Registration) ----------
if not st.session_state["logged_in"]:
    if st.session_state["registration_mode"]:
        registration_page()
    else:
        login_page()
    st.stop()
else:
    st.sidebar.markdown(f"**Logged in:** `{st.session_state['username']}`")
    st.sidebar.markdown(f"**Role:** {st.session_state['role']}")
    logout()
    if not st.session_state["onboarded"]:
        st.success(f"👋 Welcome {st.session_state['username']} to AquaChain!")
        st.info("Use the navigation bar to access different modules. Upload your latest data file in the Documents section for analytics.")
        st.session_state["onboarded"] = True

# --------- Tabbed Main Navigation ---------
menu_options = ["Home Dashboard","Orders","Shipments","Analytics","Documents","Suppliers","Settings"]
if st.session_state["role"] == "Admin":
    menu_options.append("User Management")
selected = option_menu(
    None, menu_options,
    icons=["house","boxes","truck","bar-chart","file-earmark-arrow-up","people","gear","shield-lock"],
    orientation='horizontal'
)

# --------- Alert & Notification Center ----
def get_alerts(df=None):
    alerts = []
    if df is not None and "payment_due_date" in df.columns and "paid" in df.columns:
        overdue = df[(pd.to_datetime(df["payment_due_date"]) < pd.Timestamp.today()) & (df["paid"] == False)]
        if not overdue.empty:
            alerts.append(f"⚠️ {len(overdue)} payments overdue!")
    if df is not None and "delivery_eta" in df.columns and "delivered" in df.columns:
        late = df[(pd.to_datetime(df["delivery_eta"]) < pd.Timestamp.today()) & (df["delivered"] == False)]
        if not late.empty:
            alerts.append(f"🚚 {len(late)} shipment(s) delayed!")
    return alerts

# --------- Document Upload/Download Center -----
def document_hub():
    st.subheader("Document Center")
    uploaded_docs = st.file_uploader("Upload Documents (invoices, bills, certs)", accept_multiple_files=True)
    if uploaded_docs:
        for doc in uploaded_docs:
            st.write(f"- {doc.name} uploaded.")
        st.success("Documents uploaded! (For full production use, implement secure cloud storage.)")
    st.info("Search, preview, and manage documents below (UI Placeholder).")
    doc_demo = pd.DataFrame({
        'Document Name': ['Invoice_123.pdf','COO-BatchA.pdf','Contract_Supplier7.pdf'],
        'Type': ['Invoice','Certificate','Contract'],
        'Last Modified': ['2025-06-15','2025-06-01','2025-01-21'],
        'Actions':['View','Download','View']
    })
    st.dataframe(doc_demo)

# --------- Directory (Supplier/Partner) -----
def directory_hub():
    st.subheader("Supplier Directory")
    supplier_demo = pd.DataFrame({
        "Supplier": ["Blue Aqua Ltd.","Green Oceans Co.","FishPro Farms"],
        "Contact": ["blue@aqua.com","info@greenoceans.com","fishpro@example.com"],
        "Performance Score": [92,85,89],
        "Compliance": ["Yes","Yes","No"],
        "Onboarded":["2023-07-01","2023-09-15","2024-04-20"]
    })
    st.dataframe(supplier_demo)
    st.info("Invite new suppliers or view detailed profiles (UI Placeholder).")

# --------- Settings ---------
def settings_center():
    st.subheader("Account & Portal Settings")
    st.write("Update contact info, password, notifications, and role-based preferences.")
    st.info("(Settings management UI placeholder. Implement user preference persistence in production code.)")

# --------- Home Dashboard ---------
def home_dashboard(df):
    col1, col2, col3 = st.columns(3)
    col1.metric("Live Orders", 18)      # demo value
    col2.metric("On-Time Shipments", "95%")
    col3.metric("Supplier Rating", "4.7/5")
    alerts = get_alerts(df)
    if alerts:
        for a in alerts:
            st.warning(a)
    st.subheader("Quick Links")
    st.markdown("- 📦 [Go to Orders](#orders)")
    st.markdown("- 🗂️ [Go to Shipments](#shipments)")
    st.markdown("- 📊 [Open Analytics](#analytics)")
    st.markdown("- 📁 [Upload Documents](#documents)")
    st.info("Latest platform activity and KPIs. For detailed analytics, visit the Analytics page.")
    st.success("All systems operational.")

# --------- Orders ---------
def orders_center(df):
    st.subheader("Orders Management")
    if df is not None:
        cols = ["order_id","status","created_at","payment_due_date","amount"]
        present = [col for col in cols if col in df.columns]
        st.dataframe(df[present].head(20))
    st.info("This table presents current and historical orders, filterable and searchable.")
    if st.session_state["role"] in ["Admin","Manager"]:
        st.button("Create New Order (UI)")

# --------- Shipments ---------
def shipments_center(df):
    st.subheader("Shipments")
    if df is not None and "shipment_id" in df.columns:
        st.dataframe(df[["shipment_id","status","delivery_eta","delivered"]].head(20))
    st.info("Track, manage and update all active shipments from here.")

# --------- Analytics (Network, Metrics, Bottleneck) ---------
def analytics_center(df):
    st.subheader("Supply Chain Analytics")
    if df is not None:
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
                height=500, margin=dict(l=24, r=24, t=70, b=32),
                title="Supply Chain Network Map",
                showlegend=False, plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Open Sans, Arial", size=14)
            )
            return fig

        if len(G):
            st.markdown("**Network Visualization**")
            fig = plot_graph(G)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Shows flow from supplier to customer by batch.")
        else:
            st.info("Network: Provide columns 'from_entity', 'to_entity', 'batch_id' in data.")
        if {'payment_date','delivery_date','transaction_date'}.issubset(df.columns):
            lead_times = (pd.to_datetime(df['payment_date']) - pd.to_datetime(df['delivery_date'])).dt.days
            working_cap = (pd.to_datetime(df['payment_date']) - pd.to_datetime(df['transaction_date'])).dt.days.mean()
            st.metric("Average Payment Lead Time (days)", f"{lead_times.mean():.1f}")
            st.metric("Working Capital Cycle (days)", f"{working_cap:.1f}")
        else:
            st.info("Metrics: Add 'payment_date', 'delivery_date', 'transaction_date' for finance analytics.")
        if {'start_date','end_date'}.issubset(df.columns):
            total_time = (pd.to_datetime(df['end_date']) - pd.to_datetime(df['start_date'])).dt.days
            avg = total_time.mean()
            bottlenecks = df[total_time > avg * 1.5]
            st.markdown("**Bottlenecks**")
            if not bottlenecks.empty:
                st.warning("Detected Bottlenecks in Logistics:")
                st.dataframe(bottlenecks)
            else:
                st.success("No significant bottlenecks detected.")
        else:
            st.info("Bottlenecks: Requires 'start_date', 'end_date' columns.")
    else:
        st.info("Upload your supply chain CSV in 'Documents' tab to enable analytics.")

# --------- Data Storage (Demo Fallback) ---------
@st.cache_data(show_spinner=False)
def load_demo_csv():
    demo_data = {
        'order_id':[1001,1002,1003],
        'status':['Paid','Unpaid','Paid'],
        'created_at':['2024-07-01','2024-07-02','2024-07-03'],
        'payment_due_date':['2024-07-10','2024-07-13','2024-07-16'],
        'amount':[5000,3000,4500],
        'from_entity':['Blue Aqua','Green Oceans','FishPro'],
        'to_entity':['FreshSeafood','AquaRetail','FreshSeafood'],
        'batch_id':['B001','B002','B003'],
        'payment_date':['2024-07-10','2024-07-13','2024-07-16'],
        'delivery_date':['2024-07-09','2024-07-12','2024-07-15'],
        'transaction_date':['2024-06-30','2024-07-01','2024-07-02'],
        'start_date':['2024-07-08','2024-07-10','2024-07-14'],
        'end_date':['2024-07-09','2024-07-12','2024-07-15'],
        'shipment_id':[21001,21002,21003],
        'delivered':[True,False,True],
        'delivery_eta':['2024-07-09','2024-07-12','2024-07-15'],
        'paid':[True,False,True],
    }
    return pd.DataFrame(demo_data)

# --------- Document Upload (For CSV) ---------
def get_uploaded_csv():
    if "uploaded_csv" not in st.session_state:
        st.session_state["uploaded_csv"] = None
    files = st.session_state.get("uploaded_csv", None)
    if files is not None:
        return files
    uploaded = st.sidebar.file_uploader("Upload Supply Chain CSV",type="csv")
    if uploaded is not None:
        st.session_state["uploaded_csv"] = uploaded
        return uploaded
    return None

csv_file = get_uploaded_csv()
df = None
if csv_file:
    try:
        df = pd.read_csv(csv_file)
    except Exception:
        st.sidebar.error("Error loading supply chain CSV file!")
if not csv_file:
    df = load_demo_csv() # Demo fallback

# --------- Navigation Routing ---------
if selected == "Home Dashboard":
    home_dashboard(df)
elif selected == "Orders":
    orders_center(df)
elif selected == "Shipments":
    shipments_center(df)
elif selected == "Analytics":
    analytics_center(df)
elif selected == "Documents":
    document_hub()
elif selected == "Suppliers":
    directory_hub()
elif selected == "Settings":
    settings_center()
elif selected == "User Management" and st.session_state["role"] == "Admin":
    admin_manage_users()
