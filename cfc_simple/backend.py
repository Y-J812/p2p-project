from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime, timezone
import json, sqlite3, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, 'health_earth_coach.db')
FACTORS = {
    'petrol_car': .18, 'diesel_car': .17, 'petrol_bike': .08, 'cng_car': .11,
    'ev_car': .04, 'bus': .05, 'metro': .03, 'train': .04, 'auto': .10,
    'electricity': .70, 'veg_meal': .70, 'egg_meal': 1.00,
    'chicken_meal': 2.50, 'mutton_meal': 6.00, 'lpg': 3.00,
    'food_waste': 1.50, 'mixed_waste': .10
}


def init_db():
    with sqlite3.connect(DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, input_json TEXT NOT NULL, result_json TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, question TEXT NOT NULL, answer TEXT NOT NULL)""")

def num(a, key):
    try: return max(0.0, float(a.get(key, 0) or 0))
    except (TypeError, ValueError): return 0.0

def calculate(a):
    cats = {'Transport': num(a,'transport_km_day')*30*FACTORS.get(a.get('transport_mode'),0), 'Electricity': num(a,'electricity_kwh_month')*FACTORS['electricity'], 'Food': num(a,'food_meals_week')*4.345*FACTORS.get(a.get('food_type'),0), 'LPG': num(a,'lpg_kg_month')*FACTORS['lpg'], 'Waste': (num(a,'waste_kg_week')*4.345*FACTORS['mixed_waste'])+(num(a,'food_waste_kg_week')*4.345*FACTORS['food_waste'])}
    monthly=sum(cats.values()); annual=monthly*12/1000
    return {'monthly':monthly,'annual':annual,'categories':cats}

def recommendations(a):
    out=[]
    if num(a,'transport_km_day')>8: out.append({'title':'Cut two private-vehicle trips each week','description':'Combine errands, walk short trips, or use public transport where practical.','impact':'High','cost':'Low','effort':'Easy'})
    if num(a,'electricity_kwh_month')>100: out.append({'title':'Trim cooling and appliance use','description':'Raise AC efficiency, use LEDs, and switch off avoidable loads.','impact':'High','cost':'Low','effort':'Easy'})
    if a.get('food_type') in ('mutton_meal','chicken_meal'): out.append({'title':'Swap one high-impact meal each week','description':'Try a plant-rich meal or a lower-impact protein without changing your whole diet.','impact':'Medium','cost':'Low','effort':'Easy'})
    if num(a,'food_waste_kg_week')>1: out.append({'title':'Reduce avoidable food waste','description':'Plan portions, store leftovers, and buy perishables for realistic consumption.','impact':'Medium','cost':'₹0','effort':'Easy'})
    if not out: out.append({'title':'Keep building low-carbon habits','description':'Your current inputs do not show one dominant intervention. Small consistent changes still add up.','impact':'Low','cost':'₹0','effort':'Easy'})
    return out

FAQ = {
    # Core concepts
    'what is a carbon footprint': "A carbon footprint is the estimated greenhouse-gas emissions caused directly or indirectly by an activity, person, product, service, or household. It is usually reported as carbon-dioxide equivalent (CO₂e).",
    'how is carbon footprint calculated': "This coach estimates transport, electricity, food, LPG/cooking, and waste. Each activity is multiplied by an emission factor, then the categories are added to estimate monthly and annual CO₂e.",
    'what is co2e': "CO₂e means carbon-dioxide equivalent. It puts different greenhouse gases onto one comparable scale using their climate-warming effect.",
    'what is carbon dioxide': "Carbon dioxide (CO₂) is a greenhouse gas released by activities such as burning fossil fuels, producing cement, and changing land use. It is the main gas used to describe many carbon footprints.",
    'what are greenhouse gases': "Greenhouse gases trap heat in Earth's atmosphere. Important examples include carbon dioxide, methane, nitrous oxide, and fluorinated gases.",
    'what is global warming': "Global warming is the long-term rise in Earth's average surface temperature, driven mainly by increased concentrations of heat-trapping greenhouse gases from human activities.",
    'what is climate change': "Climate change is the broader long-term change in temperatures, rainfall, seasons, oceans, and other climate patterns. Human-caused greenhouse-gas emissions are the main driver of the warming observed in recent decades.",
    'what is net zero': "Net zero means reaching a balance where human-caused greenhouse-gas emissions are reduced as far as possible and the remaining emissions are balanced by durable removals. Reducing emissions comes first.",
    'what is carbon neutral': "Carbon neutral generally means balancing emitted carbon dioxide with an equivalent amount of reductions or removals. The quality of the claim depends on what emissions are included and how the balancing is done.",
    'what is scope 1 2 3': "Scope 1 covers direct emissions from owned or controlled sources, Scope 2 covers purchased electricity, heat or steam, and Scope 3 covers other indirect value-chain emissions such as purchased goods, travel, and waste.",
    'what is a carbon offset': "A carbon offset represents a claimed reduction or removal of greenhouse gases outside your own activities. Offsets can complement direct reductions, but they should not be used as an excuse to avoid reducing your footprint.",
    'what is carbon removal': "Carbon removal takes CO₂ out of the atmosphere and stores it for a meaningful period. Examples include some reforestation, soil-carbon practices, biochar, and engineered removal methods; permanence and measurement matter.",

    # Calculation and interpretation
    'how accurate is my footprint': "Your result is an estimate, not a laboratory measurement. Accuracy depends on the activity data and emission factors. More precise distances, electricity use, food quantities, and locally appropriate factors improve the estimate.",
    'why is my footprint an estimate': "A personal footprint combines many activities whose exact emissions are not directly measured at home. We therefore multiply activity data by emission factors to create a useful estimate for decision-making.",
    'what is a good carbon footprint': "There is no single universal 'good' number because lifestyles, household sizes, climates, energy systems, and accounting boundaries differ. Use your result mainly as a baseline and focus on reducing it over time.",
    'should i compare myself with other people': "Comparisons can be useful, but they are imperfect because households and regions differ. Your own trend is usually the most actionable measure: are your emissions falling while your quality of life remains good?",
    'which category is biggest': "Your largest category depends on your current inputs. Ask 'What is my biggest source?' and I can inspect your latest calculation.",
    'how often should i calculate': "Monthly or quarterly is usually enough for a personal tracker. Recalculate after a meaningful lifestyle change so you can see whether it affected your trend.",
    'does a small change matter': "Yes. One small change may have a modest effect, but repeated changes across transport, energy, food, and waste can add up. The best first step is usually the largest practical source in your own result.",

    # Transport
    'how can i reduce transport emissions': "Reduce unnecessary private-vehicle kilometres first. Walking, cycling, public transport, ride sharing, trip chaining, and efficient routing can all help. If driving is necessary, smoother driving and a more efficient vehicle can reduce fuel use.",
    'is driving bad for the climate': "Driving is not inherently 'bad', but private fossil-fuel travel often creates substantial emissions. The impact depends on vehicle efficiency, fuel, distance, occupancy, and alternatives available to you.",
    'is an electric car carbon free': "No. An EV has no tailpipe CO₂ emissions while driving, but emissions occur during vehicle manufacturing, battery production, electricity generation, and charging. Its total footprint depends heavily on the electricity mix and vehicle size.",
    'are electric cars better': "Often, yes over their lifetime, especially when charged with lower-carbon electricity, but the result varies by vehicle size, battery, electricity mix, manufacturing, and mileage.",
    'does public transport reduce emissions': "Usually. A bus, metro, or train can spread the emissions of a trip across many passengers, often producing less CO₂e per passenger-kilometre than a private car.",
    'is cycling zero carbon': "Cycling has no tailpipe emissions, but a full lifecycle assessment can include bicycle manufacturing, maintenance, food energy, and infrastructure. It is nevertheless typically a very low-emission way to travel.",
    'is walking zero carbon': "Walking has no vehicle tailpipe emissions. A full lifecycle comparison can include food and infrastructure, but walking is generally among the lowest-emission travel options.",
    'does carpooling help': "Yes. Sharing one vehicle across more people can reduce emissions per passenger compared with everyone making the trip alone, especially when it replaces separate car trips.",
    'does flight increase carbon footprint': "Yes. Air travel can be a significant source of emissions because flights use energy-intensive fuels. Distance, aircraft, cabin class, load, and the way non-CO₂ effects are accounted for all matter.",
    'how to reduce flight emissions': "Fly less when practical, combine trips, use rail for suitable short routes, and avoid unnecessary connections. If you cannot avoid flying, choose efficient routing and understand that offsets do not replace the need for reduction.",

    # Home and electricity
    'how can i reduce electricity emissions': "Use efficient appliances, sensible cooling temperatures, LEDs, natural ventilation where practical, and avoid standby loads. Solar electricity can also reduce operational emissions where it is suitable.",
    'does air conditioning increase carbon footprint': "Usually, yes. Air conditioning can use substantial electricity, so its footprint depends on how much you use it and how carbon-intensive the electricity supply is. Efficient equipment and sensible set points can help.",
    'how can i make ac greener': "Use an efficient AC, clean filters, keep doors and windows closed while cooling, set a sensible temperature, use fans when helpful, and improve shading or insulation so the AC has less work to do.",
    'do led bulbs save carbon': "Usually. LEDs use much less electricity for the same light output and last longer than many older bulbs, so they can reduce both energy use and associated emissions.",
    'does solar reduce carbon footprint': "Usually. Solar can reduce the emissions associated with purchased electricity, although manufacturing and installation also have lifecycle emissions. The benefit depends on the system, location, and electricity it displaces.",
    'does standby power matter': "Standby loads are usually smaller than major uses such as cooling or water heating, but they can add up. Turn off or unplug devices that consume significant standby power when practical.",
    'does an inverter ac save energy': "An efficient inverter AC can use less electricity than an inefficient fixed-speed system for comparable cooling, particularly when it can modulate output rather than repeatedly cycling at full power.",
    'does refrigerator use lots of electricity': "A refrigerator runs continuously, so efficiency matters. Keep the door seals healthy, avoid excessive heat around the appliance, set appropriate temperatures, and consider an efficient model when replacing it.",

    # Food
    'is vegetarian food better for the climate': "Generally, yes. Plant-rich meals tend to have lower greenhouse-gas emissions than meals centered on ruminant meat. The exact impact varies by ingredients, production, transport, and food waste.",
    'is vegan diet lower carbon': "Often, yes. Diets centered on plants generally have lower food-related greenhouse-gas emissions than diets high in beef or mutton, although individual ingredients and farming practices still matter.",
    'is chicken better than beef': "Generally, yes. Chicken usually has a lower greenhouse-gas footprint than beef or mutton, although the exact footprint depends on production systems and what is included in the accounting.",
    'is mutton high carbon': "Yes. Ruminant meat such as mutton generally has a relatively high greenhouse-gas footprint because of methane and other emissions associated with livestock production.",
    'does local food reduce carbon': "Sometimes, but transport is only one part of food's footprint. Production methods and the type of food can matter much more than distance alone.",
    'does organic food reduce carbon': "Not automatically. Organic systems can have benefits such as reduced synthetic-input use, but their land requirements and yields can change the overall footprint. There is no universal rule that organic always means lower carbon.",
    'does food waste create carbon emissions': "Yes. Food production already uses land, energy, water, and other resources; when edible food is wasted, those upstream emissions were unnecessary. Decomposing food can also generate methane depending on the disposal system.",
    'how can i reduce food waste': "Plan portions, store food correctly, use leftovers, track what gets thrown away, freeze food when useful, and buy perishables in quantities you can realistically consume.",

    # Waste and consumption
    'how can i reduce waste emissions': "Avoid unnecessary purchases first, then reuse and repair items. Separate recyclable materials where local systems accept them, and prevent food waste. Recycling is useful, but reducing consumption is often more powerful.",
    'is recycling enough': "No. Recycling can reduce some material impacts, but avoiding unnecessary consumption, reusing products, repairing items, and extending product life usually come earlier in the waste hierarchy.",
    'does plastic create carbon emissions': "Yes. Fossil fuels are used as feedstocks for many plastics, energy is used during manufacturing, and disposal can create additional emissions. The footprint varies greatly by material, production, use, and end-of-life.",
    'should i recycle plastic': "If your local recycling system accepts that plastic, recycling can be useful. Follow local sorting rules because contamination and materials that are not actually recycled can reduce the benefit.",
    'does buying less help climate': "Usually. Every new product requires materials, manufacturing, transport, and often packaging. Keeping useful products longer, repairing them, sharing them, and buying only what you need can reduce emissions.",
    'is fast fashion bad for climate': "Fast fashion can create substantial emissions through fiber production, manufacturing, transport, and short product lifetimes. Buying fewer, longer-lasting items and using them longer can reduce impact.",

    # Nature, water and broader sustainability
    'do trees reduce carbon': "Growing trees remove CO₂ from the atmosphere while they accumulate carbon, but forests can be lost to fire, drought, pests, or land-use change. Trees are valuable, but protecting existing ecosystems and reducing emissions remain essential.",
    'how many trees offset my footprint': "There is no reliable universal tree-to-tonne conversion. Tree growth varies by species, climate, soil, age, survival, and permanence. Treat tree planting as a complement to direct emissions reductions rather than a simple one-for-one formula.",
    'does water use affect carbon footprint': "Yes, indirectly. Treating, heating, pumping, and transporting water use energy, while hot water can be a significant household energy use. Water scarcity is also an important environmental issue beyond carbon.",
    'what is a water footprint': "A water footprint estimates the freshwater used directly and indirectly to produce goods and services. It is related to sustainability but is different from a carbon footprint.",
    'what is biodiversity': "Biodiversity is the variety of life at genetic, species, and ecosystem levels. Climate change is one major pressure on biodiversity, alongside habitat loss, pollution, invasive species, and overexploitation.",
    'what is methane': "Methane (CH₄) is a powerful greenhouse gas. Important human-related sources include livestock, fossil-fuel systems, landfills, and wastewater. It has a shorter atmospheric lifetime than CO₂ but strong warming effects.",
    'what is nitrous oxide': "Nitrous oxide (N₂O) is a potent greenhouse gas associated especially with agricultural soils and fertilizer use, as well as some industrial processes and combustion.",

    # Action and behavior
    'what should i change first': "Start with your largest practical emissions category. If transport dominates, reduce private-vehicle kilometres; if electricity dominates, focus on cooling and appliance efficiency; if food dominates, shift high-impact meals and reduce waste.",
    'give me carbon saving tips': "Focus on high-impact habits: travel fewer private-vehicle kilometres, use efficient cooling and appliances, choose more plant-rich meals, reduce food waste, repair and reuse products, and avoid unnecessary purchases.",
    'what is the easiest climate action': "Choose one change that is easy to repeat: combine errands, walk a short trip, reduce AC use slightly, replace an inefficient bulb, or prevent one food-waste habit. Consistency matters more than perfection.",
    'can one person make a difference': "Yes. One person's direct footprint is only part of the story; choices also influence household habits, demand for products, workplaces, and social norms. Individual action is strongest when combined with broader system changes.",
    'is carbon footprint my fault': "A footprint is a measurement, not a moral judgment. Use it to find practical opportunities. Many emissions are shaped by infrastructure, income, technology, and available choices, so the goal is progress rather than guilt.",
    'do i need to be perfect': "No. Perfection is not required. Pick a few high-impact changes that fit your life and keep them going. A sustainable habit that lasts is usually better than an extreme change that does not.",

    # Coach capabilities / allowed conversation
    'what can you answer': "I can answer questions about carbon footprints, CO₂e, climate change, greenhouse gases, transport, electricity, food, waste, consumption, offsets, carbon removal, sustainability, and your Health Earth Coach results. I can also compare your saved assessments and explain your recommendations.",
    'help': "I can help with your footprint, explain climate and CO₂e concepts, identify your biggest sources, suggest reductions, compare previous check-ins, explain recommendations, and run what-if thinking. Ask in your own words — you do not need a special command.",
}


EXTRA_FAQ = {
    'carbon footprint of a smartphone': "A smartphone has emissions from raw materials, manufacturing, electricity use, software and networks, and end-of-life. Manufacturing is often the largest part, so keeping a phone longer can be a meaningful action.",
    'carbon footprint of a laptop': "A laptop's footprint includes materials, manufacturing, electricity use, and end-of-life. Manufacturing can be a large share, so extending the device's useful life is often one of the simplest ways to reduce its impact.",
    'carbon footprint of internet use': "Internet use has emissions from data centres, networks, and the electricity used by your devices. The footprint of a specific activity varies with data volume, network, device, and electricity sources.",
    'carbon footprint of streaming': "Streaming uses electricity in data centres, networks, and your device. Longer or higher-resolution streaming generally uses more energy, but the footprint varies substantially by infrastructure and electricity mix.",
    'carbon footprint of coffee': "Coffee's footprint depends mainly on farming, land use, processing, transport, brewing, and waste. Food production can matter more than the distance the coffee travels, and avoiding wasted coffee and using efficient brewing can help.",
    'carbon footprint of rice': "Rice can have a relatively significant food footprint because flooded rice fields can produce methane. The exact impact depends on farming practices, region, yield, and how the rice is processed.",
    'carbon footprint of dairy': "Dairy products have emissions from animal production, feed, manure, processing, refrigeration, and transport. Lower-impact choices depend on the product and production system, while reducing food waste is broadly useful.",
    'carbon footprint of eggs': "Eggs generally have a lower footprint than beef or mutton but still create emissions through feed, poultry production, processing, refrigeration, and transport.",
    'carbon footprint of clothes': "Clothing emissions come from fibre production, manufacturing, dyeing, transport, use, and end-of-life. Buying fewer durable items and keeping them in use longer can reduce impact.",
    'carbon footprint of paper': "Paper's footprint depends on forestry, pulping, manufacturing, transport, use, and disposal. Using paper efficiently, choosing recycled content where appropriate, and recycling through a functioning local system can help.",
    'carbon footprint of cement': "Cement is carbon-intensive because producing clinker releases CO₂ from both fuel use and the chemistry of limestone. Lower-carbon cement, material efficiency, and alternative binders are important ways to reduce construction emissions.",
    'carbon footprint of a house': "A home's footprint can include construction materials, electricity, heating and cooling, water heating, appliances, maintenance, and end-of-life. Operational energy and carbon-intensive materials can both matter.",
    'carbon footprint of online shopping': "Online shopping has emissions from product manufacturing, packaging, warehousing, delivery, returns, and sometimes data services. Buying only what you need, avoiding unnecessary returns, and choosing longer-lasting products can help.",
    'carbon footprint of food delivery': "Delivery adds vehicle and packaging emissions, but the meal itself can still be the largest part of the footprint. Grouping orders, avoiding unnecessary deliveries, and reducing food waste can help.",
    'carbon footprint of pets': "Pets can have an environmental footprint through food, products, waste, and services. Pet food can be a significant part, especially diets based heavily on animal products. Avoiding overfeeding and reducing waste can help.",
    'carbon footprint of bottled water': "Bottled water can have emissions from plastic or glass production, bottling, refrigeration, transport, and disposal. Where safe, treated tap water often avoids much of that packaging and transport impact.",
    'does hot water increase carbon footprint': "Yes. Heating water can use substantial energy, so shorter hot showers, efficient water heaters, sensible temperature settings, and renewable electricity can reduce associated emissions.",
    'does cooking gas create carbon emissions': "Yes. Burning LPG or other fossil fuels for cooking releases CO₂ directly. Efficient burners, pressure cookers where suitable, reducing wasted heat, and cleaner electricity options can lower emissions.",
    'is induction cooking greener': "Induction cooking is not automatically zero-carbon, but it can be efficient. Its climate benefit depends strongly on the electricity source and what cooking fuel it replaces.",
    'is a gas stove bad for climate': "Gas cooking creates direct CO₂ emissions when fuel is burned. The climate impact depends on fuel use, efficiency, leakage upstream, and what alternative cooking system would use instead.",
    'is a hybrid car better': "A hybrid can use less fuel than a comparable conventional vehicle, especially in stop-and-go driving. Its overall footprint depends on vehicle size, efficiency, manufacturing, driving pattern, and electricity use for plug-in hybrids.",
    'is a motorcycle lower carbon than a car': "Often per passenger, a motorcycle can use less fuel and material than a car, but the result depends on the vehicle, occupancy, distance, and alternative transport. Public transport, cycling, and walking can be lower still.",
    'is a bus greener than a car': "Often, especially when the bus is reasonably occupied. Emissions per passenger depend on vehicle efficiency, route, occupancy, and electricity or fuel source.",
    'is a train greener than a flight': "For many routes, especially where rail is efficient and well used, trains can have lower emissions per passenger than flights. The comparison depends on distance, train technology, occupancy, and electricity or fuel source.",
    'does remote work reduce carbon': "It can reduce commuting emissions, but the total effect depends on home energy use, office energy savings, equipment, and whether people make additional trips because they work remotely.",
    'does commuting affect carbon footprint': "Yes. Regular commuting can be a meaningful part of a personal footprint. Distance, transport mode, occupancy, fuel, and frequency all matter.",
    'how do i lower my monthly footprint': "Look at the largest category in your current result and choose one repeatable change. Common priorities are private transport, cooling and electricity, high-impact meals, and food waste.",
    'how do i lower my annual footprint': "Treat the annual number as a trend rather than a score. Make a few high-impact monthly changes, save a new assessment, and use the History section to see whether the annualized estimate falls.",
    'why did my footprint increase': "If you have multiple saved assessments, ask me to compare them. I can identify the change in annual CO₂e and the category with the biggest movement.",
    'why did my footprint decrease': "If you have multiple saved assessments, I can compare them and identify the category that contributed most to the improvement. Ask 'What changed since my last check-in?'",
    'how do i use the what if simulator': "Enter your current footprint inputs, choose a scenario such as transport, electricity, food, or combined reduction, and compare the projected annual CO₂e with your baseline.",
    'what are scope 1 emissions': "Scope 1 emissions are direct greenhouse-gas emissions from sources owned or controlled by an organisation, such as fuel burned in its own vehicles or boilers.",
    'what are scope 2 emissions': "Scope 2 emissions are indirect emissions associated with purchased electricity, steam, heating, or cooling consumed by an organisation.",
    'what are scope 3 emissions': "Scope 3 emissions are other indirect value-chain emissions, such as purchased goods, business travel, employee commuting, product use, and waste.",
    'what is a lifecycle assessment': "A lifecycle assessment evaluates environmental impacts across stages of a product or service, such as raw materials, manufacturing, transport, use, and end-of-life. It helps avoid focusing on only one stage.",
    'what is embodied carbon': "Embodied carbon refers to greenhouse-gas emissions associated with materials and products across their lifecycle, especially extraction, manufacturing, transport, construction, maintenance, and disposal.",
    'what is operational carbon': "Operational carbon is the greenhouse-gas emissions associated with using a building or product, such as electricity, heating, cooling, and other ongoing energy use.",
    'what is a carbon budget': "A carbon budget is a limit on cumulative CO₂ emissions associated with a chosen temperature goal or accounting boundary. The idea emphasizes that total emissions over time matter, not just a single year's number.",
}
FAQ.update(EXTRA_FAQ)

TERM_FAQ = {
    'methane': FAQ['what is methane'], 'ch4': FAQ['what is methane'],
    'nitrous oxide': FAQ['what is nitrous oxide'], 'n2o': FAQ['what is nitrous oxide'],
    'net zero': FAQ['what is net zero'], 'carbon neutral': FAQ['what is carbon neutral'],
    'co2e': FAQ['what is co2e'], 'co₂e': FAQ['what is co2e'],
    'global warming': FAQ['what is global warming'], 'climate change': FAQ['what is climate change'],
    'biodiversity': FAQ['what is biodiversity'], 'water footprint': FAQ['what is a water footprint'],
    'embodied carbon': FAQ['what is embodied carbon'], 'operational carbon': FAQ['what is operational carbon'],
}

# Broad, deterministic intent patterns make the assistant useful without requiring an external AI service.
# Each pattern is intentionally limited to the carbon/climate/sustainability spectrum.
INTENT_RULES = [
    (r'\b(carbon|co2|co₂|emission|emissions|greenhouse|ghg|climate|warming|net zero|carbon neutral|offset|offsets|removal|sustainab)', 'core'),
    (r'\b(footprint|my result|my emissions|my carbon|my footprint|annual|monthly)\b', 'core'),
    (r'\b(car|bike|bus|metro|train|travel|transport|commute|driv|ride|flight|fly|aviation)', 'transport'),
    (r'\b(electricity|energy|power|ac|air conditioner|cooling|refrigerator|fridge|led|solar|appliance|standby)', 'energy'),
    (r'\b(food|meal|diet|beef|mutton|chicken|meat|vegetarian|vegan|organic|local food|food waste)', 'food'),
    (r'\b(waste|garbage|trash|plastic|recycl|reuse|repair|fast fashion|consumption|buying)', 'waste'),
    (r'\b(tree|forest|biodiversity|water footprint|water use|methane|ch4|nitrous|n2o)', 'environment'),
    (r'\b(compare|previous|last week|last month|progress|compliment|complain|improv|trend)', 'progress'),
]

OUT_OF_SCOPE = (
    "Sorry, I can't answer that because it's outside the Health Earth Coach scope. 🌍 "
    "I’m here for carbon footprints, CO₂e, climate change, greenhouse gases, transport, electricity, food, waste, sustainability, offsets, and your footprint history/results."
)

GREETINGS = {
    'hi', 'hello', 'hey', 'hiya', 'good morning', 'good afternoon', 'good evening',
    'thanks', 'thank you', 'thx', 'ok', 'okay', 'bye', 'goodbye'
}

def normalize_question(q):
    q = q.lower().replace('co2', 'co₂')
    q = re.sub(r"[^a-z0-9\s₂₂₀₁₂₃₄₅₆₇₈₉_-]", ' ', q)
    return re.sub(r'\s+', ' ', q).strip()

def find_faq(q):
    ql = normalize_question(q)
    # Exact / strong phrase matching first.
    for term, answer in TERM_FAQ.items():
        if term in ql:
            return answer
    for key, answer in FAQ.items():
        keyn = normalize_question(key)
        if keyn == ql or keyn in ql:
            return answer
    # Match most of a known question when the user paraphrases it.
    best = None; best_score = 0
    stop = {'what','is','are','the','a','an','my','how','can','i','do','does','to','for','of','and','on','in','it','this','that','with','your'}
    qwords = {w for w in ql.split() if len(w) > 2 and w not in stop}
    for key, answer in FAQ.items():
        kw = {w for w in normalize_question(key).split() if len(w) > 2 and w not in stop}
        if not kw: continue
        score = len(qwords & kw) / len(kw)
        if score > best_score and len(qwords & kw) >= 2:
            best_score = score; best = answer
    return best if best_score >= 0.62 else None

def classify_scope(ql):
    # A small set of explicit out-of-domain cues prevents accidental answers to unrelated topics.
    unrelated = [
        r'\b(homework|algebra|calculus|physics|chemistry|programming|python|javascript|coding|code|debug|software|game|gaming)\b',
        r'\b(movie|movies|music|song|lyrics|celebrity|actor|actress|football|cricket|recipe|dating|relationship|politics|election|stock|crypto|investment)\b',
        r'\b(password|hack|malware|virus|medical diagnosis|medicine|symptom|disease|legal advice|lawsuit)\b',
    ]
    if any(re.search(p, ql) for p in unrelated):
        return False
    return any(re.search(p, ql) for p, _ in INTENT_RULES)

def chatbot_answer(question, context=None):
    q = question.strip()
    if not q:
        return "Ask me anything about carbon footprints, transport, energy, food, waste, CO₂e, climate, sustainability, or your saved results."
    ql = normalize_question(q)
    if ql in GREETINGS:
        if ql in {'thanks','thank you','thx'}:
            return "You're welcome! 🌍 Keep the questions coming — I'm here for carbon, climate, sustainability, and your Health Earth Coach results."
        if ql in {'bye','goodbye'}:
            return "See you next time. 🌱 Keep making small, practical changes for a healthier Earth."
        return "Hi! 🌍 I’m Earth Assistant. Ask me about carbon footprints, climate, transport, electricity, food, waste, sustainability, or your progress."

    faq = find_faq(q)
    if faq: return faq

    # Enforce the product boundary before using personal context, so unrelated
    # questions such as "recommend a movie" can never trigger footprint advice.
    if not classify_scope(ql):
        return OUT_OF_SCOPE

    # Progress questions use live saved assessments and therefore stay contextual.
    if any(re.search(p, ql) for p in [r'\bcompare\b', r'\bprevious\b', r'\blast week\b', r'\blast month\b', r'\bprogress\b', r'\bcompliment\b', r'\bcomplain\b', r'\bimprov']):
        p = progress_agent()
        if p['status'] == 'compared':
            sign='+' if p['delta_annual']>0 else ''
            return f"{p['headline']} {p['message']} Recent: {p['current']['result']['annual']:.2f} t CO₂e/year; previous: {p['previous']['result']['annual']:.2f} t CO₂e/year; change: {sign}{p['delta_annual']:.2f} t ({sign}{p['delta_percent']:.1f}%). The biggest movement was in {p['biggest_change']['category']}."
        return p['message']

    if context:
        result = calculate(context)
        biggest = max(result['categories'].items(), key=lambda x: x[1])
        if any(k in ql for k in ('my footprint','my carbon','my result','my emission','how much do i emit','how much carbon')):
            return f"Based on your current inputs, your estimated footprint is {result['annual']:.2f} t CO₂e/year ({result['monthly']:.1f} kg/month). Your largest estimated source is {biggest[0]} at about {biggest[1]:.1f} kg CO₂e/month."
        if any(k in ql for k in ('biggest','largest','main source','focus','priority')):
            return f"Your biggest estimated source is {biggest[0]} at about {biggest[1]:.1f} kg CO₂e/month. I would start there because reducing a large category usually gives the clearest result."
        if any(k in ql for k in ('recommend','suggest','what should i do','what should i change','next step')):
            recs = recommendations(context)
            return "My top recommendation is: " + recs[0]['title'] + ". " + recs[0]['description']

    # Category-level paraphrase handling.
    if any(k in ql for k in ('flight','flights','flying','aviation')):
        return "For flights, the strongest reduction is usually to avoid or replace a flight when practical. Combine trips, choose rail for suitable routes, and avoid unnecessary connections. Offsets should not replace direct reductions."
    if any(k in ql for k in ('transport','car','bike','bus','metro','train','travel','commute','driving')):
        return "For transport, prioritize fewer private-vehicle kilometres, shared/public transport, walking or cycling for short trips, and efficient routing. Avoiding a trip is usually better than making the same trip more efficiently."
    if any(k in ql for k in ('electricity','energy','ac','air conditioner','power','solar','appliance','refrigerator')):
        return "For home energy, focus on cooling, water heating, refrigeration, and inefficient appliances. LEDs and switching off idle loads help, while efficient AC settings can make a larger difference."
    if any(k in ql for k in ('food','meal','meat','chicken','mutton','beef','diet','vegetarian','vegan','food waste')):
        return "Food choices matter. Plant-rich meals generally have a lower footprint than meals centered on ruminant meat. Reducing food waste is another easy win."
    if any(k in ql for k in ('waste','garbage','recycle','recycling','plastic','reuse','repair','fashion','buy less')):
        return "Waste reduction starts with avoiding unnecessary purchases, reusing and repairing items, separating recyclable material where local systems accept it, and preventing food waste. Recycling helps, but reducing consumption is usually more powerful."
    if any(k in ql for k in ('offset','tree','trees','forest','carbon removal')):
        return "Offsets, trees, and carbon removal can complement emissions reduction, but they should not replace direct reductions. Look for transparent projects with credible measurement, additionality, and appropriate permanence."
    if any(k in ql for k in ('climate','global warming','greenhouse','methane','co2','co₂','carbon','emission','sustainability','biodiversity','water footprint')):
        return "I can explain that climate topic in the context of carbon and sustainability. Tell me what you want to know — for example, causes, measurement, personal impact, reduction strategies, or how it relates to your footprint."

    # Anything outside the defined spectrum gets a clear, friendly boundary response.
    if not classify_scope(ql):
        return OUT_OF_SCOPE
    return "I’m not sure that question is specific enough for me to answer reliably. Please rephrase it around carbon footprints, CO₂e, climate, transport, electricity, food, waste, sustainability, offsets, or your Health Earth Coach results."

def _assessment_row(row):
    return {'id': row[0], 'created_at': row[1], 'inputs': json.loads(row[2]), 'result': json.loads(row[3])}

def history_payload(limit=8):
    with sqlite3.connect(DB) as db:
        rows = db.execute('SELECT id,created_at,input_json,result_json FROM assessments ORDER BY id DESC').fetchall()
    records=[_assessment_row(r) for r in rows]
    # Keep the newest assessment for each calendar week/month.
    weeks=[]; months=[]; seen_w=set(); seen_m=set()
    for rec in records:
        dt=rec['created_at'][:10]
        try: d=datetime.fromisoformat(dt)
        except ValueError: continue
        wk=d.strftime('%Y-W%W'); mo=d.strftime('%Y-%m')
        if wk not in seen_w and len(weeks)<limit:
            seen_w.add(wk); weeks.append({'period':wk,'date':dt,'id':rec['id'],'monthly_kg':rec['result']['monthly'],'annual_t':rec['result']['annual'],'recommendations':rec['result'].get('recommendations',[])})
        if mo not in seen_m and len(months)<6:
            seen_m.add(mo); months.append({'period':mo,'date':dt,'id':rec['id'],'monthly_kg':rec['result']['monthly'],'annual_t':rec['result']['annual'],'recommendations':rec['result'].get('recommendations',[])})
    return {'weekly':weeks,'monthly':months,'count':len(records),'latest':records[0] if records else None}

def progress_agent():
    with sqlite3.connect(DB) as db:
        rows=db.execute('SELECT id,created_at,input_json,result_json FROM assessments ORDER BY id DESC LIMIT 2').fetchall()
    if not rows:
        return {'status':'no-data','headline':'Let’s create your first baseline.','message':'Calculate your footprint and I’ll start tracking your progress.','tone':'neutral'}
    current=_assessment_row(rows[0])
    if len(rows)<2:
        return {'status':'baseline','headline':'Baseline created 🌍','message':f"Your latest estimate is {current['result']['annual']:.2f} t CO₂e/year. Save another check-in after making changes and I’ll compare the two.",'tone':'positive','current':current,'previous':None}
    previous=_assessment_row(rows[1])
    cur=current['result']; prev=previous['result']
    delta=cur['annual']-prev['annual']; pct=(delta/prev['annual']*100) if prev['annual'] else 0
    if delta < -0.02:
        headline='Nice work — Earth noticed. 🌱'
        message=f"Your footprint fell by {abs(delta):.2f} t CO₂e/year ({abs(pct):.1f}%) compared with your previous check-in. That deserves a compliment. Keep the habits that drove the change."
        tone='positive'
    elif delta > 0.02:
        headline='Hey, we slipped a little. 👀'
        message=f"Your footprint increased by {delta:.2f} t CO₂e/year ({pct:.1f}%) compared with your previous check-in. That’s a constructive complaint, not a failure: let’s look at the biggest category and fix one thing first."
        tone='warning'
    else:
        headline='Steady is still progress. 🌍'
        message='Your footprint is almost unchanged from the previous check-in. I’m not going to complain — this is your chance to find one small change that moves the number next time.'
        tone='neutral'
    cat_delta={k:cur['categories'].get(k,0)-prev['categories'].get(k,0) for k in cur['categories']}
    biggest=max(cat_delta.items(), key=lambda x: abs(x[1])) if cat_delta else ('',0)
    return {'status':'compared','headline':headline,'message':message,'tone':tone,'delta_annual':delta,'delta_percent':pct,'biggest_change':{'category':biggest[0],'monthly_kg':biggest[1]},'current':current,'previous':previous}

class Handler(SimpleHTTPRequestHandler):
    server_version = 'HealthEarthCoach/1.0'
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=ROOT,**kwargs)
    def log_message(self, fmt, *args):
        print('%s - %s' % (self.address_string(), fmt % args))
    def send_json(self, data, status=200):
        body=json.dumps(data, ensure_ascii=False).encode('utf-8'); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def read_json(self):
        n=int(self.headers.get('Content-Length',0)); return json.loads(self.rfile.read(n) or '{}')
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/health': return self.send_json({'ok':True,'service':'health-earth-coach','time':datetime.now(timezone.utc).isoformat()})
        if path=='/api/factors': return self.send_json(FACTORS)
        if path=='/api/chat/history':
            with sqlite3.connect(DB) as db: rows=db.execute('SELECT id,created_at,question,answer FROM chats ORDER BY id DESC LIMIT 50').fetchall()
            return self.send_json([{'id':r[0],'created_at':r[1],'question':r[2],'answer':r[3]} for r in rows][::-1])
        if path=='/api/history': return self.send_json(history_payload())
        if path=='/api/progress': return self.send_json(progress_agent())
        if path.startswith('/api/assessments/'):
            try: aid=int(path.rsplit('/',1)[1])
            except ValueError: return self.send_json({'error':'Invalid assessment id'},400)
            with sqlite3.connect(DB) as db: row=db.execute('SELECT id,created_at,input_json,result_json FROM assessments WHERE id=?',(aid,)).fetchone()
            if not row: return self.send_json({'error':'Assessment not found'},404)
            return self.send_json({'id':row[0],'created_at':row[1],'inputs':json.loads(row[2]),'result':json.loads(row[3])})
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        try: a=self.read_json()
        except Exception: return self.send_json({'error':'Invalid JSON'},400)
        if path=='/api/calculate':
            result=calculate(a); result['recommendations']=recommendations(a); return self.send_json(result)
        if path=='/api/scenario':
            base=calculate(a); kind=a.get('scenario','combined'); reduction=0
            if kind=='transport': reduction=base['categories']['Transport']*.20*12/1000
            elif kind=='electricity': reduction=base['categories']['Electricity']*.15*12/1000
            elif kind=='food': reduction=base['categories']['Food']*.25*12/1000
            elif kind=='combined': reduction=base['annual']*.15
            return self.send_json({'base_annual':base['annual'],'reduction':reduction,'projected_annual':max(0,base['annual']-reduction)})
        if path=='/api/assessments':
            result=calculate(a); result['recommendations']=recommendations(a)
            with sqlite3.connect(DB) as db:
                cur=db.execute('INSERT INTO assessments(input_json,result_json) VALUES (?,?)',(json.dumps(a),json.dumps(result))); aid=cur.lastrowid
            return self.send_json({'id':aid,**result},201)
        if path=='/api/chat':
            answer=chatbot_answer(str(a.get('question','')), a.get('context'))
            with sqlite3.connect(DB) as db: db.execute('INSERT INTO chats(question,answer) VALUES (?,?)',(str(a.get('question','')),answer))
            return self.send_json({'answer':answer,'source':'local-carbon-coach'})
        return self.send_json({'error':'Not found'},404)

if __name__=='__main__':
    init_db(); host=os.getenv('HOST','127.0.0.1'); port=int(os.getenv('PORT','8000')); server=ThreadingHTTPServer((host,port),Handler)
    print(f'Health Earth Coach running at http://{"localhost" if host in ("0.0.0.0", "127.0.0.1") else host}:{port}')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
