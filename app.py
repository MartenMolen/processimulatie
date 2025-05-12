import streamlit as st
import simpy
import random
import io
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Processimulatie", layout="wide")
st.title("🧪 Dynamische Processimulatie met Streamlit + SimPy")

# Instellingen
aantal_orders = st.slider("Aantal orders", min_value=1, max_value=20, value=5)
simulatietijd = st.number_input("Totale simulatie tijd (tijdseenheden)", min_value=10, max_value=500, value=100)
aantal_stappen = st.number_input("Aantal processtappen", min_value=1, max_value=10, value=3)

st.markdown("---")
st.subheader("🔧 Configuratie van processtappen")

stappen_config = []
resource_config = {}

for i in range(aantal_stappen):
    st.markdown(f"**Stap {i+1}**")
    kol1, kol2, kol3, kol4 = st.columns(4)
    with kol1:
        naam = st.text_input(f"Naam stap {i+1}", value=f"Stap {i+1}", key=f"naam_{i}")
    with kol2:
        resource = st.text_input(f"Resource", value="machine", key=f"res_{i}")
    with kol3:
        capaciteit = st.number_input("Capaciteit", min_value=1, value=1, key=f"cap_{i}")
    with kol4:
        verwerkingstijd = st.number_input("Verwerkingstijd", min_value=1, value=2, key=f"tijd_{i}")

    stappen_config.append({
        "naam": naam,
        "resource": resource,
        "tijd": verwerkingstijd
    })

    if resource not in resource_config:
        resource_config[resource] = capaciteit

# Startknop
if st.button("🚀 Start simulatie"):
    output = io.StringIO()
    env = simpy.Environment()
    resources = {naam: simpy.Resource(env, capacity=cap) for naam, cap in resource_config.items()}
    resource_usage = {naam: 0 for naam in resource_config.keys()}

    def processtap(env, naam, duur, resource_obj, resource_naam):
        with resource_obj.request() as req:
            yield req
            output.write(f"{env.now:.1f}: Start {naam} ({resource_naam})\n")
            yield env.timeout(duur)
            output.write(f"{env.now:.1f}: Einde {naam}\n")
            resource_usage[resource_naam] += duur

    def order_flow(env, id):
        output.write(f"{env.now:.1f}: Order {id} binnen\n")
        for stap in stappen_config:
            yield from processtap(env, stap["naam"], stap["tijd"], resources[stap["resource"]], stap["resource"])
        output.write(f"{env.now:.1f}: Order {id} klaar\n")

    for i in range(aantal_orders):
        env.process(order_flow(env, i))
        env.timeout(1)

    env.run(until=simulatietijd)

    st.subheader("📄 Simulatielog")
    st.text_area("Log", output.getvalue(), height=300)

    st.subheader("📊 Samenvatting per resource")
    df = pd.DataFrame([
        {
            "Resource": res,
            "Verwerkingstijd": tijd,
            "Bezettingsgraad (%)": round((tijd / simulatietijd) * 100, 2)
        }
        for res, tijd in resource_usage.items()
    ])
    st.dataframe(df, use_container_width=True)

    st.subheader("📈 Bezettingsgraad per resource")
    fig = px.bar(df, x="Resource", y="Bezettingsgraad (%)", text="Bezettingsgraad (%)", color="Resource")
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
