import streamlit as st
import pandas as pd

st.title("Amazon Bearing Price Monitor")

data = pd.DataFrame({
    "time":[1,2,3,4],
    "price":[450,440,430,435]
})

st.line_chart(data.set_index("time"))