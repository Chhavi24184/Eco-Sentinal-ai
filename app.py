import pathway as pw
import random
from datetime import datetime, timedelta
import time
import os

# -------------------------
# Rainfall Stream
# -------------------------
class RainSource(pw.io.python.ConnectorSubject):
    def run(self):
        while True:
            self.next(
                timestamp=datetime.now(),
                rainfall_mm=random.randint(0, 300),
            )
            time.sleep(1)

class RainSchema(pw.Schema):
    timestamp: pw.DateTimeNaive
    rainfall_mm: int


# -------------------------
# River Level Stream
# -------------------------
class RiverSource(pw.io.python.ConnectorSubject):
    def run(self):
        while True:
            self.next(
                timestamp=datetime.now(),
                river_level=random.randint(40, 100),
            )
            time.sleep(1)

class RiverSchema(pw.Schema):
    timestamp: pw.DateTimeNaive
    river_level: int


# -------------------------
# Read Streams
# -------------------------
rain_stream = pw.io.python.read(
    RainSource(),
    schema=RainSchema,
    autocommit_duration_ms=500
)

river_stream = pw.io.python.read(
    RiverSource(),
    schema=RiverSchema,
    autocommit_duration_ms=500
)

# -------------------------
# 5-Second Sliding Window
# -------------------------
windowed_rain = rain_stream.windowby(
    pw.this.timestamp,
    window=pw.temporal.sliding(
        duration=timedelta(seconds=5),
        hop=timedelta(seconds=1),
    ),
).reduce(
    timestamp=pw.this._pw_window_end,
    avg_rainfall=pw.reducers.avg(pw.this.rainfall_mm),
)

# -------------------------
# Join Streams
# -------------------------
# -------------------------
# Temporary Combine (No Join)
# -------------------------
combined = windowed_rain.select(
    timestamp=pw.this.timestamp,
    avg_rainfall=pw.this.avg_rainfall,
    river_level=50,   # temporary fixed river value
)

# -------------------------
# Risk Logic
# -------------------------
risk_table = combined.select(
    timestamp=pw.this.timestamp,
    avg_rainfall=pw.this.avg_rainfall,
    river_level=pw.this.river_level,
    risk=pw.if_else(
        (pw.this.avg_rainfall > 200) & (pw.this.river_level > 80),
        "HIGH",
        pw.if_else(pw.this.avg_rainfall > 120, "MEDIUM", "LOW"),
    ),
)

# -------------------------
# Explanation Layer
# -------------------------
explanation_table = risk_table.select(
    timestamp=pw.this.timestamp,
    avg_rainfall=pw.this.avg_rainfall,
    river_level=pw.this.river_level,
    risk=pw.this.risk,
    explanation=pw.if_else(
        pw.this.risk == "HIGH",
        "Sustained heavy rainfall and elevated river levels detected. Flood probability is high.",
        pw.if_else(
            pw.this.risk == "MEDIUM",
            "Rainfall trend increasing. Monitor river conditions closely.",
            "Environmental conditions stable.",
        ),
    ),
)

os.makedirs(os.path.join(os.path.dirname(__file__), "web"), exist_ok=True)
pw.io.jsonlines.write(
    explanation_table,
    os.path.join(os.path.dirname(__file__), "web", "data.jsonl"),
)

# -------------------------
# Optional RAG Layer
# -------------------------
_key = os.environ.get("OPENAI_API_KEY")

if _key:
    from pathway.xpacks.llm import llms, prompts
    from pathway.xpacks.llm.document_store import DocumentStore

    doc_store = DocumentStore(source="documents/")
    llm = llms.OpenAIChat(model="gpt-4o-mini", api_key=_key)

    template = prompts.Template(
        """
        Given the environmental risk level: {risk}
        And recent rainfall average: {avg_rainfall}
        And river level: {river_level}

        Use the following documents to explain the situation:
        {context}

        Provide a clear explanation.
        """
    )

    rag_table = explanation_table.select(
        timestamp=pw.this.timestamp,
        risk=pw.this.risk,
        avg_rainfall=pw.this.avg_rainfall,
        river_level=pw.this.river_level,
        ai_explanation=doc_store.retrieve(query=pw.this.risk)
        >> template
        >> llm,
    )

    pw.io.jsonlines.write(
        rag_table,
        os.path.join(os.path.dirname(__file__), "web", "rag.jsonl"),
    )


pw.run()
