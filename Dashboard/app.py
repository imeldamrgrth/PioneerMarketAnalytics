import streamlit as st
import pandas as pd
import os
import json
import folium
import plotly.express as px
from streamlit_folium import st_folium

# PATH CONFIG
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
GEO_DIR = os.path.join(BASE_DIR, "geo")

# CONFIG
st.set_page_config(
    page_title="Pioneer Market Analytics",
    layout="wide"
)
st.title("Pioneer Market Analytics")

# LOAD DATA
@st.cache_data
def load_data():
    customers = pd.read_csv(os.path.join(DATA_DIR, "customers_dataset.csv"))
    orders = pd.read_csv(os.path.join(DATA_DIR, "orders_dataset.csv"))
    order_items = pd.read_csv(os.path.join(DATA_DIR, "order_items_dataset.csv"))
    products = pd.read_csv(os.path.join(DATA_DIR, "products_dataset.csv"))

    orders['order_purchase_timestamp'] = pd.to_datetime(
        orders['order_purchase_timestamp']
    )

    return customers, orders, order_items, products

customers, orders, order_items, products = load_data()

# LOAD GEOJSON
with open(os.path.join(GEO_DIR, "br_states.geojson"), encoding="utf-8") as f:
    brazil_geo = json.load(f)

# DATA PREPARATION
orders_customers = orders.merge(customers, on='customer_id', how='left')

# BUILD MASTER DATASET
orders_full = (
    orders_customers
    .merge(order_items, on='order_id', how='left')
    .merge(products, on='product_id', how='left')
)

# Revenue definition
orders_full['revenue'] = orders_full['price']

# SIDEBAR
st.sidebar.image("assets/logo.png", width=220)
min_date_allowed = pd.to_datetime("2016-01-01").date()
max_date_allowed = pd.to_datetime("2018-12-31").date()

with st.sidebar:
    st.subheader("Periode Analisis")

    start_date = st.date_input(
        "Periode Awal",
        value=min_date_allowed,
        min_value=min_date_allowed,
        max_value=max_date_allowed
    )

    end_date = st.date_input(
        "Periode Akhir",
        value=max_date_allowed,
        min_value=min_date_allowed,
        max_value=max_date_allowed
    )

    if start_date > end_date:
        st.warning("Periode awal tidak boleh melebihi periode akhir")
        st.stop()


# FILTER DATA 
filtered_orders = orders_full[
    (orders_full['order_purchase_timestamp'].dt.date >= start_date) &
    (orders_full['order_purchase_timestamp'].dt.date <= end_date)
]

if filtered_orders.empty:
    st.info(
        f"Tidak ada transaksi dari {start_date} sampai {end_date}."
    )
else:
    st.caption(
        f"Analisis mencakup periode {start_date} sampai {end_date} "
        f"dengan volume transaksi sebesar {filtered_orders['order_id'].nunique():,} order"
    )

# KPI SUMMARY
if not filtered_orders.empty:

    order_items = filtered_orders.merge(order_items, on='order_id', how='left')
    order_items['revenue'] = order_items['price_x'].fillna(0)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Revenue", f"R$ {order_items['revenue'].sum():,.2f}")
    with col2:
        st.metric("Total Orders", filtered_orders['order_id'].nunique())
    with col3:
        st.metric("Total Customers", filtered_orders['customer_unique_id'].nunique())

st.markdown("<br><br>", unsafe_allow_html=True)

# TABS
tabs = st.tabs([
    "Customer Segmentation",
    "Temporal Insights",
    "Category Overview",
    "Geographic Analysis"
])

tab1, tab2, tab3, tab4 = tabs

st.markdown("""
<style>
div[role="tablist"] {
    display: flex;
    justify-content: space-between; /* kunci utama */
    width: 100%;
}

div[role="tablist"] > button {
    margin: 0;
}
</style>
""", unsafe_allow_html=True)

# TAB 1: CUSTOMER SEGMENTATION
with tab1:

    if not filtered_orders.empty:

        # Build RFM Table
        snapshot_date = filtered_orders['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

        rfm = (
            order_items
            .groupby('customer_unique_id')
            .agg(
                recency=('order_purchase_timestamp', lambda x: (snapshot_date - x.max()).days),
                frequency=('order_id', 'nunique'),
                monetary=('revenue', 'sum')
            )
            .reset_index()
        )

        rfm['R_score'] = pd.qcut(rfm['recency'].rank(method='first'), 4, labels=False) + 1
        rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 4, labels=False) + 1
        rfm['M_score'] = pd.qcut(rfm['monetary'].rank(method='first'), 4, labels=False) + 1

        def rfm_segment(row):
            if row['R_score'] >= 3 and row['F_score'] >= 3 and row['M_score'] >= 3:
                return 'Champions'
            elif row['R_score'] >= 3 and row['F_score'] >= 2:
                return 'Loyal Customers'
            elif row['R_score'] >= 3:
                return 'Potential Loyalists'
            elif row['R_score'] == 2:
                return 'Need Attention'
            else:
                return 'Lost Customers'

        rfm['Segment'] = rfm.apply(rfm_segment, axis=1)

        # 1. RFM Score Distribution
        st.markdown("### Distribution of RFM Scores")

        col1, col2, col3 = st.columns(3)

        with col1:
            fig_r = px.histogram(
                rfm, x='recency',
                title="Recency Distribution",
                nbins=30
            )
            st.plotly_chart(fig_r, use_container_width=True)

        with col2:
            fig_f = px.histogram(
                rfm, x='frequency',
                title="Frequency Distribution",
                nbins=30
            )
            st.plotly_chart(fig_f, use_container_width=True)

        with col3:
            fig_m = px.histogram(
                rfm, x='monetary',
                title="Monetary Distribution",
                nbins=30
            )
            st.plotly_chart(fig_m, use_container_width=True)

        # 2. Customer Segment Distribution
        st.markdown("### Customer Segment Distribution")

        segment_count = (
            rfm['Segment']
            .value_counts()
            .reset_index()
        )
        segment_count.columns = ['Segment', 'Total Customers']

        fig_segment = px.bar(
            segment_count,
            x='Segment',
            y='Total Customers',
            text='Total Customers'
        )
        st.plotly_chart(fig_segment, use_container_width=True)

        # 3. Revenue Contribution by Segment
        st.markdown("### Revenue Contribution by Segment")

        segment_revenue = (
            rfm.groupby('Segment')['monetary']
            .sum()
            .reset_index()
        )

        fig_revenue = px.pie(
            segment_revenue,
            names='Segment',
            values='monetary',
            hole=0.4
        )
        st.plotly_chart(fig_revenue, use_container_width=True)

    else:
        st.info("Data tidak tersedia untuk analisis segmentasi.")


    # KEY INSIGHTS 
    st.markdown("### Key Insights")

    total_customers = rfm.shape[0]
    total_revenue = rfm['monetary'].sum()

    segment_summary = (
        rfm.groupby('Segment')
        .agg(
            customers=('customer_unique_id', 'count'),
            revenue=('monetary', 'sum')
        )
        .reset_index()
    )

    # Hitung proporsi
    segment_summary['customer_pct'] = segment_summary['customers'] / total_customers * 100
    segment_summary['revenue_pct'] = segment_summary['revenue'] / total_revenue * 100

    # Dominant Revenue Segment
    top_segment = segment_summary.sort_values('revenue', ascending=False).iloc[0]

    st.success(
        f"**Revenue Concentration**: "
        f"Segmen **{top_segment['Segment']}** menyumbang "
        f"**{top_segment['revenue_pct']:.1f}% dari total revenue**, "
        f"meskipun hanya mencakup **{top_segment['customer_pct']:.1f}% dari total pelanggan**. "
        f"Segmen ini merupakan penggerak utama pendapatan bisnis."
    )

    # Customer Base Health
    lost_segment = segment_summary[segment_summary['Segment'] == 'Lost Customers']
    if not lost_segment.empty:
        lost_pct = lost_segment['customer_pct'].values[0]
        st.warning(
            f"**Customer Attrition Risk**: "
            f"Sebanyak **{lost_pct:.1f}% pelanggan** berada dalam segmen *Lost Customers*. "
            f"Hal ini mengindikasikan potensi kehilangan pendapatan jika tidak dilakukan strategi reaktivasi."
        )

    # Growth Opportunity
    potential_segment = segment_summary[
        segment_summary['Segment'].isin(['Potential Loyalists', 'Need Attention'])
    ]

    if not potential_segment.empty:
        pot_pct = potential_segment['customer_pct'].sum()
        st.info(
            f"**Growth Opportunity**: "
            f"Segmen *Potential Loyalists* dan *Need Attention* mencakup "
            f"**{pot_pct:.1f}% dari basis pelanggan**. "
            f"Segmen ini memiliki peluang besar untuk ditingkatkan menjadi pelanggan bernilai tinggi "
            f"melalui strategi engagement dan promosi yang tepat."
        )

# TAB 2: TEMPORAL INSIGHTS
with tab2:

    if not filtered_orders.empty:

        # 1. Daily Transaction Volume
        st.markdown("### Daily Transaction Volume (Day of Week)")

        daily = (
            filtered_orders
            .groupby(filtered_orders['order_purchase_timestamp'].dt.day_name())
            .size()
            .reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
            .reset_index(name='Total Transactions')
        )
        daily.columns = ['Day', 'Total Transactions']

        fig_daily = px.line(
            daily,
            x='Day',
            y='Total Transactions',
            markers=True,
            title=None
        )
        st.plotly_chart(fig_daily, use_container_width=True)

        # 2. Hourly Transaction Distribution
        st.markdown("### Hourly Transaction Distribution")

        hourly = (
            filtered_orders
            .groupby(filtered_orders['order_purchase_timestamp'].dt.hour)
            .size()
            .reset_index(name='Total Transactions')
        )
        hourly.columns = ['Hour', 'Total Transactions']

        fig_hourly = px.bar(
            hourly,
            x='Hour',
            y='Total Transactions',
            title=None
        )
        st.plotly_chart(fig_hourly, use_container_width=True)

        # 3. Monthly Transaction Trend
        st.markdown("### Monthly Transaction Trend")

        monthly = (
            filtered_orders
            .groupby(filtered_orders['order_purchase_timestamp'].dt.to_period('M'))
            .size()
            .reset_index(name='Total Transactions')
        )
        monthly['Month'] = monthly['order_purchase_timestamp'].astype(str)

        fig_monthly = px.line(
            monthly,
            x='Month',
            y='Total Transactions',
            markers=True,
            title=None
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    else:
        st.info("Tidak ada data untuk analisis temporal.")


    # TEMPORAL INSIGHTS
    st.markdown("### Key Insights")

    # Daily Insight
    daily_summary = (
        filtered_orders
        .groupby(filtered_orders['order_purchase_timestamp'].dt.day_name())
        .size()
        .reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
        .reset_index(name='Total Transactions')
    )

    peak_day = daily_summary.loc[daily_summary['Total Transactions'].idxmax()]

    st.success(
        f"**Peak Transaction Day**: "
        f"Hari dengan volume transaksi tertinggi adalah **{peak_day['order_purchase_timestamp']}**, "
        f"dengan total **{peak_day['Total Transactions']:,} transaksi**. "
        f"Hal ini menunjukkan potensi optimalisasi promosi dan kesiapan operasional pada hari tersebut."
    )

    # Hourly Insight
    hourly_summary = (
        filtered_orders
        .groupby(filtered_orders['order_purchase_timestamp'].dt.hour)
        .size()
        .reset_index(name='Total Transactions')
    )

    peak_hour = hourly_summary.loc[hourly_summary['Total Transactions'].idxmax()]

    st.info(
        f"**Peak Operating Hour**: "
        f"Jam paling sibuk terjadi pada **pukul {int(peak_hour['order_purchase_timestamp']):02d}.00**, "
        f"dengan **{peak_hour['Total Transactions']:,} transaksi**. "
        f"Periode ini krusial untuk menjaga performa sistem, logistik, dan customer support."
    )

    # Weekend vs Weekday Insight
    filtered_orders['day_type'] = filtered_orders['order_purchase_timestamp'].dt.dayofweek.apply(
        lambda x: 'Weekend' if x >= 5 else 'Weekday'
    )

    day_type_summary = (
        filtered_orders
        .groupby('day_type')
        .size()
        .reset_index(name='Total Transactions')
    )

    weekend = day_type_summary[day_type_summary['day_type'] == 'Weekend']['Total Transactions'].values[0]
    weekday = day_type_summary[day_type_summary['day_type'] == 'Weekday']['Total Transactions'].values[0]

    if weekend > weekday:
        st.warning(
            f"**Weekend-Dominant Behavior**: "
            f"Volume transaksi pada akhir pekan lebih tinggi dibanding hari kerja. "
            f"Strategi kampanye dan ketersediaan stok sebaiknya difokuskan pada periode akhir pekan."
        )
    else:
        st.warning(
            f"**Weekday-Dominant Behavior**: "
            f"Sebagian besar transaksi terjadi pada hari kerja. "
            f"Optimalisasi jam kerja dan proses fulfillment di weekday menjadi faktor kunci performa."
        )

    # Monthly Trend Insight
    monthly_summary = (
        filtered_orders
        .groupby(filtered_orders['order_purchase_timestamp'].dt.to_period('M'))
        .size()
        .reset_index(name='Total Transactions')
    )

    monthly_summary['Month'] = monthly_summary['order_purchase_timestamp'].astype(str)

    if monthly_summary.shape[0] >= 2:
        trend_diff = monthly_summary.iloc[-1]['Total Transactions'] - monthly_summary.iloc[-2]['Total Transactions']

        if trend_diff > 0:
            st.success(
                f"**Positive Momentum**: "
                f"Terjadi peningkatan volume transaksi pada periode terbaru. "
                f"Hal ini mengindikasikan momentum pertumbuhan yang positif dan peluang untuk scale-up aktivitas bisnis."
            )
        else:
            st.error(
                f"**Demand Slowdown Signal**: "
                f"Volume transaksi mengalami penurunan pada periode terbaru. "
                f"Diperlukan evaluasi terhadap strategi pemasaran atau faktor eksternal yang memengaruhi demand."
            )

# TAB 3: CATEGORY OVERVIEW
with tab3:

    if not orders_full.empty:

        # DATA PREP
        category_summary = (
            orders_full
            .groupby('product_category_name')
            .agg(
                revenue=('revenue', 'sum'),
                total_orders=('order_id', 'nunique'),
                product_count=('product_id', 'nunique')
            )
            .reset_index()
        )

        category_summary['AOV'] = category_summary['revenue'] / category_summary['total_orders']

        # ROW 1
        col1, col2 = st.columns(2)

        # Revenue per Category
        with col1:
            st.markdown("### Revenue by Product Category")

            fig_rev = px.bar(
                category_summary.sort_values('revenue', ascending=False),
                x='revenue',
                y='product_category_name',
                orientation='h'
            )
            st.plotly_chart(fig_rev, use_container_width=True)

        # Product Count per Category
        with col2:
            st.markdown("### Product Count by Category")

            fig_count = px.bar(
                category_summary.sort_values('product_count', ascending=False),
                x='product_count',
                y='product_category_name'
            )
            st.plotly_chart(fig_count, use_container_width=True)

        # ROW 2
        col3, col4 = st.columns(2)

        # Average Order Value
        with col3:
            st.markdown("### Average Order Value (AOV) by Category")

            fig_aov = px.bar(
                category_summary.sort_values('AOV', ascending=False),
                x='AOV',
                y='product_category_name',
                orientation='h'
            )
            st.plotly_chart(fig_aov, use_container_width=True)

        # Top Products
        with col4:
            st.markdown("### Top 10 Products by Revenue")

            top_products = (
                orders_full
                .groupby('product_category_name')
                .agg(
                    revenue=('revenue', 'sum'),
                    total_orders=('order_id', 'nunique')
                )
                .sort_values('revenue', ascending=False)
                .head(10)
                .reset_index()
            )

            st.dataframe(
                top_products,
                use_container_width=True,
                hide_index=True
            )

    else:
        st.info("Data produk tidak tersedia.")


    # CATEGORY INSIGHTS
    st.markdown("### Key Insights")

    total_revenue = category_summary['revenue'].sum()

    category_summary['revenue_pct'] = category_summary['revenue'] / total_revenue * 100

    # Revenue Dominance
    top_cat = category_summary.sort_values('revenue', ascending=False).iloc[0]

    st.success(
        f"**Revenue Driver**: "
        f"Kategori **{top_cat['product_category_name']}** merupakan kontributor utama "
        f"dengan **{top_cat['revenue_pct']:.1f}% dari total revenue**. "
        f"Ketergantungan yang tinggi pada kategori ini perlu dikelola dengan strategi diversifikasi."
    )

    # Diversification Insight
    low_product_cat = category_summary.sort_values('product_count').iloc[0]

    st.warning(
        f"**Portfolio Concentration**: "
        f"Kategori **{low_product_cat['product_category_name']}** memiliki jumlah produk relatif sedikit. "
        f"Hal ini dapat membatasi potensi pertumbuhan kategori tersebut jika permintaan meningkat."
    )

    # High Value Category
    high_aov_cat = category_summary.sort_values('AOV', ascending=False).iloc[0]

    st.info(
        f"**High-Value Transactions**: "
        f"Kategori **{high_aov_cat['product_category_name']}** memiliki "
        f"rata-rata nilai transaksi tertinggi. "
        f"Kategori ini berpotensi untuk strategi premium pricing atau upselling."
    )


# TAB 4: GEOSPATIAL INSIGHTS
with tab4:
    if not filtered_orders.empty:

    
        # DATA PREPARATION
        geo_summary = (
            filtered_orders
            .groupby('customer_state', as_index=False)
            .agg(
                total_revenue=('revenue', 'sum'),
                total_orders=('order_id', 'nunique'),
                total_customers=('customer_unique_id', 'nunique')
            )
        )

        # Revenue per State (Choropleth Map)
        st.markdown("### Revenue Distribution by State")

        map_data = geo_summary[['customer_state', 'total_revenue']]

        # Base map Brazil
        m = folium.Map(
            location=[-14.2350, -51.9253],
            zoom_start=4,
            tiles="cartodbpositron"
        )

        # Choropleth layer
        folium.Choropleth(
            geo_data=brazil_geo,
            data=map_data,
            columns=["customer_state", "total_revenue"],
            key_on="feature.properties.sigla",
            fill_color="YlGnBu",
            fill_opacity=0.7,
            line_opacity=0.3,
            legend_name="Total Revenue per State"
        ).add_to(m)

        st_folium(m, width=900, height=500)

        # Top States by Orders (Horizontal Bar Chart)
        st.markdown("### Top States by Number of Orders")

        top_states_orders = geo_summary.sort_values(
            'total_orders', ascending=True
        )

        fig_orders = px.bar(
            top_states_orders.sort_values('total_orders', ascending=True),
            x='total_orders',
            y='customer_state',
            orientation='h',
            labels={
                'total_orders': 'Total Orders',
                'customer_state': 'State'
            },
        title="Order Volume by State"
        )

        st.plotly_chart(fig_orders, use_container_width=True)


        # Customer Density per State
        # (Proxy karena tidak ada koordinat lat-long)
        st.markdown("### Customer Distribution by State")

        top_states_customers = geo_summary.sort_values(
            'total_customers', ascending=True
        )

        fig_customers = px.bar(
            top_states_customers,
            x='total_customers',
            y='customer_state',
            orientation='h',
            labels={
                'total_customers': 'Number of Customers',
                'customer_state': 'State'
            },
            title="Customer Density by State"
        )

        st.plotly_chart(fig_customers, use_container_width=True)

        # Regional KPI Table
        st.markdown("### Regional Performance Summary")

        geo_kpi = geo_summary.copy()
        geo_kpi['revenue_per_order'] = (
            geo_kpi['total_revenue'] / geo_kpi['total_orders']
        )

        st.dataframe(
            geo_kpi.sort_values('total_revenue', ascending=False),
            use_container_width=True
        )

        # Business Insight (Auto-generated)
        top_revenue_state = geo_summary.loc[
            geo_summary['total_revenue'].idxmax()
        ]

        top_order_state = geo_summary.loc[
            geo_summary['total_orders'].idxmax()
        ]


    # GEOGRAPHIC INSIGHTS
    st.markdown("### Key Insights")

    # Total metrics
    total_revenue = geo_summary['total_revenue'].sum()
    total_orders = geo_summary['total_orders'].sum()

    geo_summary['revenue_pct'] = geo_summary['total_revenue'] / total_revenue * 100
    geo_summary['order_pct'] = geo_summary['total_orders'] / total_orders * 100

    # Revenue Dominant Region
    top_revenue_state = geo_summary.sort_values(
        'total_revenue', ascending=False
    ).iloc[0]

    st.success(
        f"**Revenue Stronghold**: "
        f"State **{top_revenue_state['customer_state']}** menjadi kontributor revenue terbesar "
        f"dengan **{top_revenue_state['revenue_pct']:.1f}% dari total revenue nasional**. "
        f"Wilayah ini mencerminkan **market dengan daya beli tinggi** dan cocok untuk strategi "
        f"premium product atau margin optimization."
    )

    # High Volume Region
    top_order_state = geo_summary.sort_values(
        'total_orders', ascending=False
    ).iloc[0]

    st.info(
        f"**Transaction Hotspot**: "
        f"State **{top_order_state['customer_state']}** mencatat volume order tertinggi "
        f"(**{top_order_state['order_pct']:.1f}% dari total order**), "
        f"menunjukkan **aktivitas transaksi yang sangat intens**. "
        f"Wilayah ini ideal untuk strategi **akuisisi, promosi, dan operational scaling**."
    )

    # Revenue vs Volume Gap
    geo_summary['revenue_per_order'] = (
        geo_summary['total_revenue'] / geo_summary['total_orders']
    )

    high_value_state = geo_summary.sort_values(
        'revenue_per_order', ascending=False
    ).iloc[0]

    st.warning(
        f"**Behavioral Gap Across Regions**: "
        f"State **{high_value_state['customer_state']}** memiliki **revenue per order tertinggi**, "
        f"mengindikasikan **pola belanja bernilai tinggi meskipun volume transaksi tidak dominan**. "
        f"Perbedaan ini menegaskan bahwa **strategi regional tidak dapat disamaratakan**."
    )