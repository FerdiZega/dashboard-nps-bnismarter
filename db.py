from sqlalchemy import create_engine
import pandas as pd

# GANTI sesuai DB kamu
DB_URL = "postgresql://USER:PASSWORD@HOST:PORT/DATABASE"

engine = create_engine(DB_URL)

def query_db(sql):
    return pd.read_sql(sql, engine)

def write_db(df, table="nps_master"):
    df.to_sql(table, engine, index=False, if_exists="append")
