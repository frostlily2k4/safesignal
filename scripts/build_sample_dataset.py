"""Builds data/dataset.csv: a small synthetic starter dataset (English + Tanglish).

This exists so the app runs out of the box. For better results, replace
data/dataset.csv with a larger labelled dataset (same columns: text,label).
Run:  python scripts/build_sample_dataset.py
"""
import csv
import itertools
import random
from pathlib import Path

random.seed(7)
OUT = Path(__file__).resolve().parents[1] / "data" / "dataset.csv"

places = ["college", "the library", "the bus stop", "my hostel", "the office", "the mall", "T Nagar", "the canteen", "the metro station", "home"]
times = ["at 5", "after class", "tomorrow morning", "tonight", "on Saturday", "in 10 minutes"]
people = ["Amma", "Priya", "my roommate", "the team", "Kavya", "my cousin", "ma'am", "everyone"]

safe = []
safe += [f"I'll reach {p} {t}, see you there" for p, t in itertools.product(places, times)][:40]
safe += [f"Did {who} send the notes for tomorrow's exam?" for who in people]
safe += [f"Can you pick up groceries on the way back from {p}?" for p in places]
safe += [f"{who} is asking if we are free {t} for lunch" for who, t in itertools.product(people, times)][:30]
safe += [f"Reached {p} safely, will call you later" for p in places]
safe += [f"Saapadu aachu? I'm at {p} now" for p in places]
safe += [f"Naalaiku {p} la meet pannalam, {who} kooda varuvaanga" for p, who in itertools.product(places[:6], people[:5])]
safe += [f"Enna padam paakalam {t}?" for t in times]
safe += [f"Bus late aagudhu, {p} reach panna konjam late aagum" for p in places]
# everyday greetings and short replies (so normal chit-chat isn't flagged)
safe += [
    "hi", "hello", "hey", "ok", "okay", "ok da", "ok ma", "sure", "thanks", "thank you", "good night",
    "good morning", "hi, how are you?", "hello, how are you doing", "hey what's up", "fine, you?",
    "yes", "no", "hmm", "lol", "haha that's funny", "see you", "bye", "take care", "Ok ma, take care",
    "epdi iruka?", "nalla irukken", "saptiya?", "seri", "sari da", "romba thanks", "enna panra?",
    "Hi, nice to meet you", "Congrats on the result!", "Happy birthday!",
    "Call me when free", "On the way", "Will reply later, in class", "Done, sent it", "Super, thanks da",
]
# contrastive SAFE: danger words in news, fiction, academic or joking contexts
contrastive = [
    "The documentary on stalking awareness was really eye-opening",
    "Our sociology assignment is about cyber harassment laws in India",
    "In the novel the villain threatens to kill the king, such a twist",
    "This traffic is killing me, I'll be late",
    "The news said police arrested a gang running OTP scams",
    "We discussed sextortion cases in the cyber law lecture today",
    "That thriller movie had a kidnapping scene, so scary",
    "My phone battery is dead, I'll message when I'm home",
    "Don't tell anyone about the surprise party for Priya!",
    "Delete the blurry photo from the group, I'll send a better one",
    "Send me the photo of the timetable please",
    "Can you share your location so I can book the cab to your place?",
    "Where are you now? Mom is asking if you reached",
    "The workshop on women's safety apps is on Friday",
    "I'll kill this exam, studied all night",
    "Pay the fee for the hackathon before Sunday",
    "The bank sent an alert saying never share your OTP, good reminder",
    "Enga iruka? Amma ketaanga, reach aaitiya?",
    "Photo anuppu da, group photo nalla vandhuchaa paakanum",
    "Last chance to register for the coding contest!",
    "Article says acid attack survivors are now running a cafe, so inspiring",
    "I followed you on Instagram, follow back!",
    "I saw you at the fest, your dance was amazing",
    "Our project detects harassment messages using machine learning",
    "Self-defence class is near my hostel, want to join?",
]
safe += contrastive * 3  # weight these up; duplicates are removed by text below
safe = [s for s in safe]

possible = []
possible += [f"Why didn't you reply? I've been waiting outside {p} for an hour" for p in ["your college", "your hostel", "your office", "the library"]]
possible += [f"Send me your live location {t}, I want to know where you are" for t in times]
possible += [f"Don't tell {who} we're talking, they won't understand" for who in ["your parents", "your friends", "anyone", "your amma", "your sister"]]
possible += [f"Come alone {t}, don't bring your friends" for t in times]
possible += [f"Why are you ignoring me? I can see you're online {t}" for t in ["now", "every night", "all day", "again"]]
possible += [f"Who were you with at {p}? Tell me now" for p in places]
possible += [f"Send me a selfie {t}, just for me" for t in times]
possible += [f"You looked nice at {p} today, I was watching you" for p in places]
possible += [f"Enga iruka ippo? Location anuppu {t}" for t in times]
possible += [f"Yaarkittayum sollatha, idhu namma secret" + s for s in ["", " ok", " sari", " promise"]]
possible += [f"Thaniya vaa {t}, friends ah kootitu varadha" for t in times]
possible += [f"Unga hostel kitta than irukken, keela vaa" + s for s in ["", " please", " ippo"]]
possible += [
    "Your KYC will be suspended today, click this link to update",
    "I got your number from your friend, can we chat privately?",
    "You don't need your friends, I'm the only one who cares about you",
    "Delete our chat after reading, it's better that way",
    "Video call me now alone, nobody else should be there",
    "I know your class timings, I'll wait near the gate",
    "Why did you block me on Insta? Unblock me or I'll keep messaging",
    "Send me 2000 urgently, I'll explain later, don't ask questions",
    "Your parcel is held, pay the customs fee on this UPI to release it",
    "If you were really my friend you would send that pic",
    "I keep seeing you near your PG every evening",
    "Answer my calls, I won't stop until you do",
    "Photo anuppu, yaarukkum kaatamaaten",
    "Late night ah chat pannalam, un amma ku theriya vendam",
    "Share the OTP you just got, it's for verifying your prize",
]

threat = []
threat += [f"If you don't send the pics I will leak your {x} to everyone" for x in ["chats", "photos", "videos", "messages"]]
threat += [f"I will hurt you if you go to {p} again" for p in places]
threat += [f"I know where you live, I'm coming to {p} {t}" for p, t in itertools.product(["your house", "your hostel", "your college"], times)]
threat += [f"Pay me {amt} or your photos go viral tonight" for amt in ["5000", "10000", "Rs 20000", "₹50000"]]
threat += [f"You'll regret this, I will {x} you" for x in ["finish", "destroy", "kill", "ruin"]]
threat += [f"Unless you meet me {t} I'll send these photos to your parents" for t in times]
threat += [f"Help, someone is following me near {p}" for p in places]
threat += [f"He is outside my door and won't leave, call {x}" for x in ["police", "112", "someone", "amma"]]
threat += [f"Un photos ah viral aakiduven, {t} panam anuppu" for t in ["ippove", "naalaiku kulla", "tonight", "1 hour la"]]
threat += [f"Unna kolluven, {p} pakkam vandha" for p in ["college", "hostel", "office"]]
threat += [f"Vida maaten unna, {x}" for x in ["paathuko", "wait pannu", "nyabagam vechuko"]]
threat += [
    "I will throw acid on your face if you say no",
    "Last warning, reply now or I'll come to your house",
    "I have your private video, do what I say or everyone sees it",
    "I'm going to kill you and nobody will find out",
    "Send money now or I post the morphed pics on Instagram",
    "Someone grabbed my hand at the bus stop, I'm scared, come fast",
    "He's been following me for 20 minutes, I'm hiding in a shop",
    "You owe me, either you come tonight or I'll tell your family everything",
    "I'll make your life hell, I know your college and your friends",
    "Leak pannuven unna pathi ellaathaiyum, careful ah iru",
    "Adichiduven, innoru vaati ignore pannina",
    "Help me please, a man is forcing me into his car",
    "Your morphed photos are ready, transfer 10000 or they go to your contacts",
]

rows = [(t, "SAFE") for t in safe] + [(t, "POSSIBLE_THREAT") for t in possible] + [(t, "THREAT") for t in threat]
seen, final = set(), []
for t, l in rows:
    if t not in seen:
        seen.add(t)
        final.append((t, l))
random.shuffle(final)
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["text", "label"])
    w.writerows(final)
from collections import Counter
print(f"Wrote {len(final)} rows to {OUT}: {Counter(l for _, l in final)}")
