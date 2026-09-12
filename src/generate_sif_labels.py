import pandas as pd
import numpy as np
import re
from pathlib import Path

INPUT = Path("output/sanketak_master_clean.csv")
OUTPUT = Path("output/sanketak_master_labeled.csv")

df = pd.read_csv(INPUT)

# ------------------------------------------------------------
# COMBINE ALL AVAILABLE INFORMATION
# ------------------------------------------------------------

text = (
    df["NARRATIVE"].fillna("").astype(str) + " " +
    df["ACTIVITY"].fillna("").astype(str) + " " +
    df["HAZARD"].fillna("").astype(str) + " " +
    df["FAILURE_MODE"].fillna("").astype(str) + " " +
    df["CONSEQUENCE"].fillna("").astype(str)
).str.lower()


def contains(pattern):
    # non-capturing groups -> no regex warning
    return text.str.contains(pattern, regex=True, na=False)


# ------------------------------------------------------------
# POSITIVE SIGNALS
# ------------------------------------------------------------

high_hazard = contains(
    r"\b("
    r"explosion|exploded|dust explosion|gas explosion|"
    r"roof fall|roof collapse|ground fall|rock fall|"
    r"highwall|"
    r"engulfed|buried|crushed|trapped|entrapped|"
    r"overturn|overturned|rollover|rolled over|tipped over|"
    r"hoist|hoisting|load fell|bucket fell|"
    r"electrical|electrocution|electric shock|"
    r"power line|energized|arc flash|"
    r"fire|flame|ignition|"
    r"inundation|flood|water engulf|submerged|"
    r"drowning|fall from height|"
    r"struck by|caught between"
    r")\b"
)

worker_exposure = contains(
    r"\b("
    r"employee|employees|worker|workers|"
    r"miner|miners|operator|operators|"
    r"driver|foreman|supervisor|crew|personnel|"
    r"working|operating|driving|inside|"
    r"near|nearby|under|"
    r"trapped|entrapped|pinned|caught"
    r")\b"
)

escape_rescue = contains(
    r"\b("
    r"escaped|escape|rescued|rescue|"
    r"extricated|evacuated|mayday|"
    r"trapped|pinned|"
    r"removed from cab|removed from truck|"
    r"remained in truck|remained in cab"
    r")\b"
)

severe_mechanism = contains(
    r"\b("
    r"fatal|fatality|killed|died|death|"
    r"crushed|crushing|"
    r"pinned|"
    r"amputation|amputated|"
    r"electrocuted|"
    r"engulfed|buried|"
    r"submerged|drowning|"
    r"serious injury|"
    r"fractured|fracture"
    r")\b"
)

# ------------------------------------------------------------
# STRUCTURED HIGH-RISK CATEGORIES
# ------------------------------------------------------------

high_risk_hazard = df["HAZARD"].fillna("").str.upper().isin([
    "FALL OF ROOF OR BACK",
    "FALL OF FACE/RIB/PILLAR/SIDE/HIGHWALL",
    "ENTRAPMENT",
    "ELECTRICAL",
    "IGNITION OR EXPLOSION OF GAS OR DUST",
    "EXPLODING VESSELS UNDER PRESSURE",
    "FIRE",
    "INUNDATION",
    "POWERED HAULAGE",
    "HOISTING",
    "EXPLOSIVES AND BREAKING AGENTS"
])

# ------------------------------------------------------------
# NEGATIVE SIGNALS
# ------------------------------------------------------------

no_exposure = contains(
    r"\b("
    r"unoccupied|"
    r"no employees|no employee|"
    r"no workers|"
    r"no personnel|"
    r"no one was|"
    r"no one injured|"
    r"property damage only|"
    r"away from active|"
    r"not working in area"
    r")\b"
)

minor_event = contains(
    r"\b("
    r"minor|small scratch|minor cut|minor bruise|"
    r"first aid only|"
    r"no injury|no injuries|"
    r"no lost time"
    r")\b"
)


# ------------------------------------------------------------
# SCORE
# ------------------------------------------------------------

score = pd.Series(0, index=df.index)

score += high_hazard.astype(int) * 2
score += worker_exposure.astype(int) * 2
score += escape_rescue.astype(int) * 3
score += severe_mechanism.astype(int) * 2
score += high_risk_hazard.astype(int) * 2

score -= no_exposure.astype(int) * 4
score -= minor_event.astype(int) * 3

df["SIF_SCORE"] = score


# ------------------------------------------------------------
# LABEL
# ------------------------------------------------------------

df["SIF_POTENTIAL"] = -1
df["SIF_RATIONALE"] = ""

# Positive
positive = score >= 4

df.loc[positive, "SIF_POTENTIAL"] = 1
df.loc[positive, "SIF_RATIONALE"] = (
    "High-risk hazard with evidence of worker exposure, "
    "severe mechanism, or escape/rescue."
)

# Negative
negative = score <= 0

df.loc[negative, "SIF_POTENTIAL"] = 0
df.loc[negative, "SIF_RATIONALE"] = (
    "Insufficient SIF indicators or clear evidence of "
    "low/no worker exposure."
)

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

df.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8"
)

print("=" * 60)
print("IMPROVED SIF LABELING COMPLETE")
print("=" * 60)

print("\nLabel distribution:")
print(df["SIF_POTENTIAL"].value_counts())

print("\nPercentages:")
print(
    df["SIF_POTENTIAL"]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)

print("\nScore distribution:")
print(df["SIF_SCORE"].describe())

print("\nSaved:", OUTPUT)