import streamlit as st
import pandas as pd
from data_loader import load_transactions, load_batches, load_logistics
from network_model import build_supply_chain_graph, compute_payment_lead_times, compute_working_capital, detect_bottlenecks
from visualizations import plot_supply_chain_graph

st.set_page_config(page_title="Aquaculture Supply Chain Dashboard", layout="wide")

st.title("Aquaculture Supply Chain Finance & Traceability Dashboard")

# -- Data Loading
st.header("Load Supply Chain Data")
transactions = load_transactions()
batches = load_batches()
logistics = load_logistics()
st.success("Data loaded successfully.")

# -- Build Graph & Show Visualization
st.header("Supply Chain Network Visualization")
G = build_supply_chain_graph(transactions, batches, logistics)
fig = plot_supply_chain_graph(G)
st.plotly_chart(fig, use_container_width=True)

# -- Key Metrics
st.header("Key Metrics")
lead_times = compute_payment_lead_times(transactions)
working_capital = compute_working_capital(transactions)
st.metric("Avg. Payment Lead Time (days)", round(lead_times.mean(), 1))
st.metric("Avg. Working Capital Cycle (days)", round(working_capital, 1))

# -- Bottlenecks
st.header("Bottleneck Detection")
bottlenecks = detect_bottlenecks(logistics)
if len(bottlenecks) > 0:
    st.write("Detected bottlenecks:")
    st.dataframe(bottlenecks)
else:
    st.write("No bottlenecks detected.")

# -- Scenario Simulation (placeholder for future enhancements)
st.header("Scenario Simulation")
st.info("Adjust payment or logistics settings here in future releases.")

st.sidebar.title("Upload Data")
uploaded_transactions = st.sidebar.file_uploader("Upload transactions CSV", type="csv")
uploaded_batches = st.sidebar.file_uploader("Upload batches CSV", type="csv")
uploaded_logistics = st.sidebar.file_uploader("Upload logistics CSV", type="csv")
