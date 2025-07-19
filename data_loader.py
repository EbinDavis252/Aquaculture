import pandas as pd
from sqlalchemy import create_engine
from config import DATABASE_URI

def load_transactions():
    engine = create_engine(DATABASE_URI)
    return pd.read_sql('SELECT * FROM transactions', engine)

def load_batches():
    engine = create_engine(DATABASE_URI)
    return pd.read_sql('SELECT * FROM batches', engine)

def load_logistics():
    engine = create_engine(DATABASE_URI)
    return pd.read_sql('SELECT * FROM logistics', engine)
