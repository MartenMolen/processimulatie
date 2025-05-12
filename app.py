import streamlit as st
import simpy
import io
import pandas as pd
import plotly.express as px
import math

# ===== Hulpfuncties voor tijd conversie =====
def hms_to_seconds(h, m, s):
    return h * 3600 + m * 60 + s

def seconds_to_hms_str(secs):
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

st.set_page_config(page_title="Processimulatie met kosten en capaciteit", layout="wide")
st.title("🧪 Geavanceerde processimulatie (met tijd in hh:mm:ss)")

aantal_items = st.number_input("Aantal eenheden te verwerken", min_value=1, value=10)

# Resourceconfiguratie
st.markdown("---")
st.subheader("⚙️ Resources")
aantal_resources = st.number_input("Aantal verschillende resources", min_value=1, max_value=10, value=2)
resource_info = {}

for i in range(aantal_resources):
    st.markdown(f"**Resource {i+1}**")
    cols = st.columns(5)
    naam = cols[0].text_input("Naam", key=f"res_naam_{i}", value=f"Resource_{i+1}")
    h_val = cols[1].number_input("Uur", min_value=0, max_value=999, key=f"h_{i}")
    m_val = cols[2].number_input("Min", min_value=0, max_value=59, key=f"m_{i}")
    s_val = cols[3].number_input("Sec", min_value=0, max_value=59, key=f"s_{i}")
    kosten = cols[4].number_input("Kosten per tijdseenheid", min_value=0.0, value=50.0, key=f"kosten_{i}")
    beschikbaarheid = hms_to_seconds(h_val, m_val, s_val)
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
    kol1, kol2, kol3 = st.columns(3)
    stap_naam = kol1.text_input("Naam van de stap", value=f"Stap_{i+1}", key=f"stap_{i}")
    resource = kol2.selectbox("Resource", options=list(resource_info.keys()), key=f"res_stap_{i}")
    capaciteit = kol3.number_input("Capaciteit (hoeveel tegelijk)", min_value=1, value=1, key=f"cap_{i}")
    hh, mm, ss = st.columns(3)
    hh_val = hh.number_input("Uur", min_value=0, key=f"hh_{i}")
    mm_val = mm.number_input("Min", min_value=0, max_value=59, key=f"mm_{i}")
    ss_val = ss.number_input("Sec", min_value=0, max_value=59, key=f"ss_{i}")
    verwerkingstijd = hms_to_seconds(hh_val, mm_val, ss_val)
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

    sim_resources = {stap["naam"]: simpy.Resource(env, capacity=stap["capaciteit"]) for stap in stappen_config}
    stap_stats = {s["naam"]: {"verwerkingstijd": 0, "aantal": 0, "kosten": 0, "resource": s["resource"], "eenheden": 0} for s in stappen_config}
    resource_usage = {naam: 0 for naam in resource_info}

    def processtap(env, stap, eenheden):
        resource = sim_resources[stap["naam"]]
        resource_naam = stap["resource"]
        beschikbaarheid = resource_info[resource_naam]["beschikbaar"]
        succesvol_verwerkt = 0
        sets = math.ceil(eenheden / stap["capaciteit"])

        for i in range(sets):
            duur = stap["tijd"]
            if resource_usage[resource_naam] + duur > beschikbaarheid:
                output.write(f"{seconds_to_hms_str(env.now)}: ⛔ Resource {resource_naam} heeft onvoldoende capaciteit voor {stap['naam']} (set {i+1})\n")
                continue
            with resource.request() as req:
                res = env.process(req)
                yield res
                output.write(f"{seconds_to_hms_str(env.now)}: Start {stap['naam']} (set {i+1})\n")
                yield env.timeout(duur)
                output.write(f"{seconds_to_hms_str(env.now)}: Einde {stap['naam']} (set {i+1})\n")
                resource_usage[resource_naam] += duur
                stap_stats[stap["naam"]]["verwerkingstijd"] += duur
                stap_stats[stap["naam"]]["aantal"] += 1
                items_in_set = min(stap["capaciteit"], eenheden - succesvol_verwerkt)
                stap_stats[stap["naam"]]["eenheden"] += items_in_set
                succesvol_verwerkt += items_in_set

        result = env.event()
        result.succeed(succesvol_verwerkt)
        return result

    def item_flow(env):
        batch = 1
        stap_buffers = [aantal_items] + [0] * (len(stappen_config) - 1)

        while any(stap_buffers):
            for i, stap in enumerate(stappen_config):
                if stap_buffers[i] <= 0:
                    continue
                items = stap_buffers[i]
                proces = env.process(processtap(env, stap, items))
                verwerkt = yield proces
                stap_buffers[i] -= verwerkt
                if i + 1 < len(stap_buffers):
                    stap_buffers[i+1] += verwerkt

    env.process(item_flow(env))
    env.run()

    st.subheader("📄 Simulatielog")
    st.text_area("Log", output.getvalue(), height=300)

    totale_verwerkingstijd = env.now
    st.success(f"✅ Totale verwerkingstijd: {seconds_to_hms_str(totale_verwerkingstijd)}")

    totale_kosten = 0
    for stap_naam, data in stap_stats.items():
        res = data["resource"]
        tijd = data["verwerkingstijd"]
        res_kosten = (resource_info[res]["kosten"] / resource_info[res]["beschikbaar"]) * tijd if resource_info[res]["beschikbaar"] > 0 else 0
        data["kosten"] = res_kosten
        totale_kosten += res_kosten

    st.info(f"💰 Totale kosten: €{totale_kosten:.2f}")

    st.subheader("📊 Overzicht per processtap")
    df_stap = pd.DataFrame([
        {
            "Stap": naam,
            "Aantal keer uitgevoerd": data["aantal"],
            "Eenheden verwerkt": data["eenheden"],
            "Totale verwerkingstijd": seconds_to_hms_str(data["verwerkingstijd"]),
            "Kosten (€)": round(data["kosten"], 2)
        }
        for naam, data in stap_stats.items()
    ])
    st.dataframe(df_stap, use_container_width=True)

    st.subheader("📊 Overzicht per resource")
    df_res = pd.DataFrame([
        {
            "Resource": naam,
            "Totale verwerkingstijd": seconds_to_hms_str(tijd),
            "Beschikbaarheid": seconds_to_hms_str(resource_info[naam]["beschikbaar"]),
            "Bezettingsgraad (%)": round((tijd / resource_info[naam]["beschikbaar"]) * 100, 2) if resource_info[naam]["beschikbaar"] > 0 else 0,
            "Kosten (€)": round((tijd / resource_info[naam]["beschikbaar"]) * resource_info[naam]["kosten"], 2) if resource_info[naam]["beschikbaar"] > 0 else 0
        }
        for naam, tijd in resource_usage.items()
    ])
    st.dataframe(df_res, use_container_width=True)

    st.subheader("📈 Verwerkingstijd per resource")
    fig = px.bar(df_res, x="Resource", y=["Bezettingsgraad (%)"], text_auto=True, color="Resource")
    st.plotly_chart(fig, use_container_width=True)
