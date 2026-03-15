from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from analytics.price_analysis import AnalyticsService
from config.settings import get_settings
from database.connection import init_database
from database.repository import MonitoringRepository


st.set_page_config(
    page_title="Amazon Bearing Monitor",
    page_icon=":bar_chart:",
    layout="wide",
)

settings = get_settings()
repository = MonitoringRepository(init_database(settings.database_url))
if settings.seed_demo_data:
    repository.ensure_seed_data()
analytics = AnalyticsService(repository)


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def _format_currency(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"Rs {value:,.2f}"


def _location_label(pincode: str) -> str:
    labels = {
        "600001": "600001 Chennai",
        "560001": "560001 Bangalore",
        "110001": "110001 Delhi",
    }
    return labels.get(pincode, pincode)


products = repository.list_products()
product_options = {f"{item['asin']} | {item['title']}": item["asin"] for item in products}

st.title("Real-Time Price Monitoring System")
st.caption("Amazon India bearing market intelligence for distributors and pricing teams")

left, right = st.columns([2, 1])

with left:
    selected_label = st.selectbox("Product Search", options=list(product_options) or ["No products"])
    selected_asin = product_options.get(selected_label)

with right:
    location_filter = st.selectbox(
        "Location Filter",
        options=["All"] + settings.location_pincodes,
        format_func=lambda value: "All locations" if value == "All" else _location_label(value),
    )

summary = analytics.build_summary(selected_asin)
price_frame = repository.price_history_frame(selected_asin)
offers_frame = repository.latest_market_snapshot()
if selected_asin and not offers_frame.empty:
    offers_frame = offers_frame[offers_frame["asin"] == selected_asin]
buy_box_frame = repository.buy_box_frame(selected_asin)
alerts_frame = pd.DataFrame(repository.list_alerts(25))

if location_filter != "All":
    if not price_frame.empty:
        price_frame = price_frame[price_frame["location"] == location_filter]
    if not offers_frame.empty:
        offers_frame = offers_frame[offers_frame["location"] == location_filter]
    if not buy_box_frame.empty:
        buy_box_frame = buy_box_frame[buy_box_frame["location"] == location_filter]

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Products Tracked", int(price_frame["asin"].nunique()) if not price_frame.empty else 0)
metric_2.metric("Price Points", int(len(price_frame)))
metric_3.metric(
    "Avg Market Price",
    _format_currency(float(price_frame["price"].dropna().mean()))
    if not price_frame.empty and price_frame["price"].notna().any()
    else "N/A",
)
metric_4.metric(
    "Lowest Current Offer",
    _format_currency(float(offers_frame["offer_price"].min()))
    if not offers_frame.empty and offers_frame["offer_price"].notna().any()
    else "N/A",
    offers_frame.sort_values("offer_price").iloc[0]["seller_name"]
    if not offers_frame.empty and offers_frame["offer_price"].notna().any()
    else None,
)

overview_col, ranking_col = st.columns([2, 1])

with overview_col:
    st.subheader("Price Trend")
    if price_frame.empty:
        st.info("No price history available yet.")
    else:
        trend = (
            price_frame.sort_values("captured_at")
            .pivot_table(index="captured_at", columns="seller_name", values="price", aggfunc="last")
        )
        st.line_chart(trend)

    st.subheader("Real-Time Price Table")
    if offers_frame.empty:
        st.info("No seller offers available.")
    else:
        display_offers = offers_frame.sort_values(["asin", "offer_price", "seller_name"]).rename(
            columns={
                "asin": "ASIN",
                "title": "Product",
                "seller_name": "Seller",
                "location": "Pincode",
                "offer_price": "Price",
                "is_buy_box": "Buy Box",
                "is_fba": "FBA",
                "availability": "Availability",
                "captured_at": "Captured At",
            }
        )
        st.dataframe(display_offers, width="stretch")
        st.download_button(
            "Export Price Table CSV",
            data=_csv_bytes(display_offers),
            file_name="real_time_price_table.csv",
            mime="text/csv",
        )

with ranking_col:
    st.subheader("Seller Ranking")
    market_share = pd.DataFrame(summary["seller_market_share"])
    if market_share.empty:
        st.info("Seller ranking will appear after data collection.")
    else:
        st.bar_chart(market_share.set_index("seller_name"))

    st.subheader("Buy Box Win Rate")
    buy_box_rate = pd.DataFrame(summary["buy_box_win_rate"])
    if buy_box_rate.empty:
        st.info("No Buy Box history available.")
    else:
        st.bar_chart(buy_box_rate.set_index("seller_name"))

compare_col, heatmap_col = st.columns(2)

with compare_col:
    st.subheader("Seller Comparison")
    if offers_frame.empty:
        st.info("No seller comparison data available.")
    else:
        comparison = offers_frame[["seller_name", "offer_price", "is_buy_box", "is_fba", "availability", "location"]]
        st.dataframe(comparison, width="stretch")

with heatmap_col:
    st.subheader("Location-Based Price Heatmap")
    heatmap = analytics.price_heatmap(selected_asin)
    if location_filter != "All" and not heatmap.empty and location_filter in heatmap.columns:
        heatmap = heatmap[[location_filter]]
    if heatmap.empty:
        st.info("Not enough data for heatmap rendering.")
    else:
        st.dataframe(heatmap.style.format("Rs {:.2f}", na_rep="-"), width="stretch")

history_col, alert_col = st.columns(2)

with history_col:
    st.subheader("Buy Box History")
    if buy_box_frame.empty:
        st.info("No Buy Box events tracked.")
    else:
        st.dataframe(buy_box_frame, width="stretch")

with alert_col:
    st.subheader("Recent Alerts")
    if alerts_frame.empty:
        st.info("No alert events recorded.")
    else:
        st.dataframe(alerts_frame, width="stretch")
        st.download_button(
            "Download Alerts Report",
            data=_csv_bytes(alerts_frame),
            file_name="alerts_report.csv",
            mime="text/csv",
        )

st.subheader("Frequent Price Changers")
changes = pd.DataFrame(summary["frequent_price_changers"])
if changes.empty:
    st.info("No price changes detected yet.")
else:
    st.dataframe(changes, width="stretch")

st.subheader("Undercutting Detection")
undercutting = pd.DataFrame(summary["undercutting_events"])
if undercutting.empty:
    st.info("No undercutting events detected.")
else:
    st.dataframe(undercutting, width="stretch")
