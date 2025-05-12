import streamlit as st
import simpy
import random
import io

# Simulatie-instellingen via gebruikersinvoer
st.title("Processimulatie met SimPy + Streamlit")

aantal_orders = st.slider("Aantal orders", min_value=1, max_value=20, value=5)
kans_productie_a = st.slider("Kans op Productie A (in %)", min_value=0, max_value=100, value=70)
simulatietijd = st.number_input("Totale simulatie tijd", min_value=10, max_value=500, value=100)

# Interne buffer voor log
output = io.StringIO()

class ProcessResources:
    def __init__(self, env):
        self.machine = simpy.Resource(env, capacity=1)
        self.operator = simpy.Resource(env, capacity=1)

def processtap(env, naam, duur, resource, res_type):
    with resource.request() as req:
        yield req
        output.write(f"{env.now:.1f}: Start {naam} ({res_type})\n")
        yield env.timeout(duur)
        output.write(f"{env.now:.1f}: Einde {naam}\n")

def keuze_gateway():
    return random.choices(['pad_a', 'pad_b'], weights=[kans_productie_a, 100 - kans_productie_a])[0]

def order_flow(env, resources, id):
    output.write(f"{env.now:.1f}: Order {id} binnen\n")
    yield from processtap(env, f"Orderregistratie", 2, resources.operator, "operator")

    keuze = keuze_gateway()
    if keuze == 'pad_a':
        yield from processtap(env, f"Productie A", 5, resources.machine, "machine")
    else:
        yield from processtap(env, f"Productie B", 3, resources.machine, "machine")

    yield from processtap(env, f"Controle & Verzending", 4, resources.operator, "operator")
    output.write(f"{env.now:.1f}: Order {id} klaar\n")

def run_simulatie():
    env = simpy.Environment()
    resources = ProcessResources(env)

    for i in range(aantal_orders):
        env.process(order_flow(env, resources, i))
        env.timeout(1)

    env.run(until=simulatietijd)

if st.button("Start simulatie"):
    output = io.StringIO()  # reset log
    run_simulatie()
    st.text_area("Simulatie-log", output.getvalue(), height=400)
