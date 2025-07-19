import networkx as nx

def build_supply_chain_graph(transactions, batches, logistics):
    G = nx.DiGraph()
    # Add batch nodes
    for _, batch in batches.iterrows():
        G.add_node(batch['batch_id'], type='batch', origin=batch['origin'])
    # Add stakeholder nodes and edges
    for _, row in transactions.iterrows():
        G.add_node(row['from_entity'], type='entity')
        G.add_node(row['to_entity'], type='entity')
        G.add_edge(row['from_entity'],
                   row['to_entity'],
                   batch_id=row['batch_id'],
                   date=row['transaction_date'],
                   payment_term=row['payment_term'])
    # Add logistics edges
    for _, row in logistics.iterrows():
        G.add_edge(row['from_location'], row['to_location'], date=row['move_date'], cost=row['logistics_cost'])
    return G

def compute_payment_lead_times(transactions):
    return (pd.to_datetime(transactions['payment_date']) - pd.to_datetime(transactions['delivery_date'])).dt.days

def compute_working_capital(transactions):
    cycle = (pd.to_datetime(transactions['payment_date']) - pd.to_datetime(transactions['transaction_date'])).dt.days
    return cycle.mean()

def detect_bottlenecks(logistics):
    # Nodes/edges with high delays vs. average
    avg_time = (pd.to_datetime(logistics['end_date']) - pd.to_datetime(logistics['start_date'])).dt.days.mean()
    outliers = logistics[
        (pd.to_datetime(logistics['end_date']) - pd.to_datetime(logistics['start_date'])).dt.days > avg_time * 1.5]
    return outliers
