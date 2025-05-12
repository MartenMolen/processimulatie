import streamlit as st
import simpy
import io
import pandas as pd
import plotly.express as px
import math

st.set_page_config(page_title="Processimulatie met kosten en capaciteit", layout="wide")
st.title("🧪 Geavanceerde processimulatie")

aantal_items = st.number_input("Aantal eenheden te verwerken", min_value=1, value=10)

# Resourceconfiguratie
st.markdown("---")
st.subheader("⚙️ Resources")

aantal_resources = st.number_input("Aantal verschillende resources", min_value=1, max_value=10, value=2)
resource_info = {}

for i in range(aantal_resources):
    st.markdown(f"**Resource {i+1}**")
    cols = st.columns(3)
    naam = cols[0].text_input(f"Naam", key=f"res_naam_{i}", value=f"Resource_{i+1}")
    beschikbaarheid = cols[1].number_input(f"Beschikbaarheid (tijdseenheden)", min_value=1, value=100, key=f"beschik_{i}")
    kosten = cols[2].number_input(f"Kosten per beschikbare periode", min_value=0.0, value=50.0, key=f"kosten_{i}")
    resource_info[naam] = {
        "beschikbaar": beschikbaarheid,
        "kosten": kosten
    }

# Processtappen
st.markdown("---")
st.subheader("📋 Processtappen")

aantal_stappen = st.number_input("Aantal processtappen", min_value=1, max_value=10, value=3)
stappen_config = []

for i in range(aantal_stappen):
    st.markdown(f"**Stap {i+1}**")
    kol1, kol2, kol3, kol4 = st.columns(4)
    stap_naam = kol1.text_input(f"Naam van de stap", value=f"Stap_{i+1}", key=f"stap_{i}")
    resource = kol2.selectbox("Resource", options=list(resource_info.keys()), key=f"res_stap_{i}")
    capaciteit = kol3.number_input("Capaciteit (hoeveel tegelijk)", min_value=1, value=1, key=f"cap_{i}")
    verwerkingstijd = kol4.number_input("Verwerkingstijd per eenheid", min_value=1.0, value=2.0, key=f"tijd_{i}")
    stappen_config.append({
        "naam": stap_naam,
        "resource": resource,
        "capaciteit": capaciteit,
        "tijd": verwerkingstijd
    })

# Simulatie starten
if st.button("🚀 Start simulatie"):
    output = io.StringIO()
    env = simpy.Environment()
    
    # SimPy resources aanmaken
    sim_resources = {
        naam: simpy.Resource(env, capacity=1000)  # hoge capaciteit, capaciteit regelen we zelf
        for naam in resource_info
    }
    
    # Voor rapportage
    stap_stats = {s["naam"]: {"verwerkingstijd": 0, "aantal": 0, "kosten": 0} for s in stappen_config}
    resource_usage = {naam: 0 for naam in resource_info}
    
    def processtap(env, stap, eenheden):
        resource = sim_resources[stap["resource"]]
        sets = math.ceil(eenheden / stap["capaciteit"])
        for i in range(sets):
            with resource.request() as req:
                yield req
                duur = stap["tijd"]
                output.write(f"{env.now:.1f}: Start {stap['naam']} (set {i+1})\n")
                yield env.timeout(duur)
                output.write(f"{env.now:.1f}: Einde {stap['naam']} (set {i+1})\n")
                stap_stats[stap["naam"]]["verwerkingstijd"] += duur
                stap_stats[stap["naam"]]["aantal"] += 1
                resource_usage[stap["resource"]] += duur

    def item_flow(env):
        for stap in stappen_config:
            yield env.process(processtap(env, stap, aantal_items))

    env.process(item_flow(env))
    env.run()

    st.subheader("📄 Simulatielog")
    st.text_area("Log", output.getvalue(), height=300)

    totale_verwerkingstijd = max(env.now for _ in range(1))
    st.success(f"✅ Totale verwerkingstijd: {totale_verwerkingstijd:.2f} tijdseenheden")

    # Totale kosten berekenen
    totale_kosten = 0
    for stap in stappen_config:
        res = stap["resource"]
        fractie_gebruik = resource_usage[res] / resource_info[res]["beschikbaar"]
        kosten = fractie_gebruik * resource_info[res]["kosten"]
        stap_stats[stap["naam"]]["kosten"] += kosten
        totale_kosten += kosten

    st.info(f"💰 Totale kosten: €{totale_kosten:.2f}")

    # Overzicht per stap
    st.subheader("📊 Overzicht per processtap")
    df_stap = pd.DataFrame([
        {
            "Stap": naam,
            "Aantal keer uitgevoerd": data["aantal"],
            "Totale verwerkingstijd": data["verwerkingstijd"],
            "Kosten (€)": round(data["kosten"], 2)
        }
        for naam, data in stap_stats.items()
    ])
    st.dataframe(df_stap, use_container_width=True)

    # Overzicht per resource
    st.subheader("📊 Overzicht per resource")
    df_res = pd.DataFrame([
        {
            "Resource": naam,
            "Totale verwerkingstijd": tijd,
            "Beschikbaarheid": resource_info[naam]["beschikbaar"],
            "Bezettingsgraad (%)": round((tijd / resource_info[naam]["beschikbaar"]) * 100, 2),
            "Kosten (€)": round((tijd / resource_info[naam]["beschikbaar"]) * resource_info[naam]["kosten"], 2)
        }
        for naam, tijd in resource_usage.items()
    ])
    st.dataframe(df_res, use_container_width=True)

    # Optionele visualisatie
    st.subheader("📈 Verwerkingstijd per resource")
    fig = px.bar(df_res, x="Resource", y="Totale verwerkingstijd", text="Totale verwerkingstijd", color="Resource")
    st.plotly_chart(fig, use_container_width=True)
