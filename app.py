# AI Travel Buddy — Gradio app
# ------------------------------------------------------------
# A low-code, recruiter-playable travel itinerary generator.
# - Quirk slider (conventional → offbeat)
# - Personalization (budget, pace, vibe, must/avoid, companions)
# - Structured JSON output → rendered to Markdown
# - Export to Markdown file
#
# Deployment: Local or Hugging Face Spaces (Gradio)
# ------------------------------------------------------------

import os
import json
import re
from typing import Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv

import gradio as gr

# --- LLM Provider (OpenAI by default) -----------------------
# This uses "openai==0.28.1" for simplicity & stability.
# If you want the newest SDK, switch to "from openai import OpenAI"
# and update the call in `call_llm()` accordingly.
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.4"))


@dataclass
class TripConfig:
    destination: str
    days: int
    budget_level: str            # "shoestring", "moderate", "premium", "luxury"
    pace: str                    # "relaxed", "balanced", "packed"
    vibe: str                    # "foodie", "outdoors", "culture", "nightlife", "family", "romantic", "mixed"
    companions: str              # "solo", "couple", "friends", "family", "business"
    dietary: str                 # "none", "vegetarian", "vegan", "halal", "kosher", "gluten-free", "other"
    must_do: str                 # free text
    avoid: str                   # free text
    quirkiness: int              # 0..100
    month_hint: str              # optional text like "April" or "Oct 2025"


JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string", "description": "Short intro & how the plan suits the user."},
        "daily_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "morning": {"type": "string"},
                    "afternoon": {"type": "string"},
                    "evening": {"type": "string"},
                    "dining": {"type": "string"}
                },
                "required": ["day", "morning", "afternoon", "evening"]
            }
        },
        "highlights": {"type": "array", "items": {"type": "string"}},
        "offbeat_picks": {"type": "array", "items": {"type": "string"}},
        "budget_breakdown": {
            "type": "object",
            "properties": {
                "lodging_per_night": {"type": "string"},
                "food_per_day": {"type": "string"},
                "transport": {"type": "string"},
                "activities": {"type": "string"},
                "total_estimate": {"type": "string"}
            }
        },
        "tips": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["overview", "daily_plan"]
}


def build_prompt(cfg: TripConfig) -> str:
    """Constructs the system + user prompt for the LLM."""
    vibe_txt = cfg.vibe if cfg.vibe != "mixed" else "a balanced mix of food, outdoors, culture, and nightlife"
    quirk_desc = "conventional & popular" if cfg.quirkiness <= 20 else \
                 "balanced with a few offbeat gems" if cfg.quirkiness <= 60 else \
                 "playfully offbeat, local, and unusual"
    month_hint = f" The trip is around: {cfg.month_hint}." if cfg.month_hint.strip() else ""

    return f"""
You are **AI Travel Buddy**, a helpful travel planner that outputs **valid JSON** conforming to this schema:
{json.dumps(JSON_SCHEMA, indent=2)}

Key rules:
- Always return **ONLY** JSON (no markdown, no commentary).
- Tailor to the user's preferences and constraints.
- Respect **dietary** needs and **avoid** list.
- Calibrate **quirkiness**: {cfg.quirkiness}/100 → {quirk_desc}.
- Prefer walkable clusters and logical neighborhood groupings.
- Include at least 1-2 **offbeat picks** if quirkiness > 30.
- Budget levels: shoestring, moderate, premium, luxury.
- If month/season provided, align with weather/seasonal factors.
- Safety: Avoid risky/illegal suggestions. No medical/legal advice.

User request:
- Destination: {cfg.destination}
- Duration (days): {cfg.days}
- Budget level: {cfg.budget_level}
- Pace: {cfg.pace}
- Vibe: {vibe_txt}
- Companions: {cfg.companions}
- Dietary: {cfg.dietary}
- Must-do: {cfg.must_do or "none"}
- Avoid: {cfg.avoid or "none"}
- Quirkiness: {cfg.quirkiness}/100.{month_hint}

Output requirements:
- Provide a concise "overview" explaining how the plan matches the inputs.
- Create a "daily_plan" with day numbers 1..N and clear morning/afternoon/evening blocks.
- "dining" can be included with suggestions relevant to dietary needs.
- Provide optional "highlights", "offbeat_picks", "budget_breakdown", "tips", "sources".
- **Return only JSON.**
"""


def extract_json(s: str) -> Dict[str, Any]:
    """Tries to extract and parse JSON from an LLM response robustly."""
    # Common pitfall: model adds ```json fences — strip them.
    s = s.strip()
    code_fence = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
    m = code_fence.match(s)
    if m:
        s = m.group(1).strip()

    # Try direct parse first
    try:
        return json.loads(s)
    except Exception:
        pass

    # Fallback: find first {...} block
    brace_stack = []
    start = None
    for i, ch in enumerate(s):
        if ch == "{":
            if not brace_stack:
                start = i
            brace_stack.append(ch)
        elif ch == "}":
            if brace_stack:
                brace_stack.pop()
                if not brace_stack and start is not None:
                    candidate = s[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        start = None  # keep scanning
    # Last resort: empty scaffold
    return {"overview": "Could not parse JSON from model.", "daily_plan": []}


def render_markdown(plan: Dict[str, Any]) -> str:
    """Converts the JSON plan into a readable Markdown itinerary."""
    md = []
    md.append(f"# Itinerary for {plan.get('destination','your trip')}")
    if 'overview' in plan:
        md.append(f"\n**Overview**\n\n{plan['overview']}\n")

    daily = plan.get("daily_plan", [])
    if daily:
        md.append("## Daily Plan\n")
        for day in daily:
            d = day.get("day", "?")
            morning = day.get("morning", "")
            afternoon = day.get("afternoon", "")
            evening = day.get("evening", "")
            dining = day.get("dining", "")
            md.append(f"### Day {d}\n- **Morning:** {morning}\n- **Afternoon:** {afternoon}\n- **Evening:** {evening}")
            if dining:
                md.append(f"- **Dining ideas:** {dining}")
            md.append("")

    if plan.get("highlights"):
        md.append("## Highlights\n" + "\n".join([f"- {h}" for h in plan["highlights"]]) + "\n")

    if plan.get("offbeat_picks"):
        md.append("## Offbeat Picks\n" + "\n".join([f"- {h}" for h in plan["offbeat_picks"]]) + "\n")

    if plan.get("budget_breakdown"):
        b = plan["budget_breakdown"]
        md.append("## Budget Breakdown\n")
        for k, v in b.items():
            md.append(f"- **{k.replace('_',' ').title()}**: {v}")
        md.append("")

    if plan.get("tips"):
        md.append("## Tips\n" + "\n".join([f"- {t}" for t in plan["tips"]]) + "\n")

    if plan.get("sources"):
        md.append("## Sources\n" + "\n".join([f"- {s}" for s in plan["sources"]]) + "\n")

    return "\n".join(md)


def call_llm(prompt: str, model: str = None, temperature: float = None, max_tokens: int = 1200) -> str:
    """Calls OpenAI Chat Completions (classic SDK for simplicity)."""
    model = model or DEFAULT_MODEL
    temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
    if not openai.api_key:
        # Graceful message to UI
        return json.dumps({
            "overview": "OPENAI_API_KEY not set. Please add your key to `.env` or your deployment secrets.",
            "daily_plan": []
        })
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": "You are a JSON-only travel planner."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return json.dumps({
            "overview": f"Error calling model: {str(e)}",
            "daily_plan": []
        })


def plan_trip(
    destination, days, budget_level, pace, vibe, companions,
    dietary, must_do, avoid, quirkiness, month_hint, model, temperature
) -> Tuple[str, dict]:
    cfg = TripConfig(
        destination=destination.strip() or "Surprise Me",
        days=int(days),
        budget_level=budget_level,
        pace=pace,
        vibe=vibe,
        companions=companions,
        dietary=dietary,
        must_do=must_do.strip(),
        avoid=avoid.strip(),
        quirkiness=int(quirkiness),
        month_hint=month_hint.strip()
    )
    prompt = build_prompt(cfg)
    raw = call_llm(prompt, model=model, temperature=temperature)
    data = extract_json(raw)

    # Add destination to JSON for rendering header
    data.setdefault("destination", cfg.destination)
    md = render_markdown(data)
    return md, data


def export_markdown(md_text: str) -> str:
    """Save markdown to a file and return path for download."""
    os.makedirs("exports", exist_ok=True)
    fname = f"exports/itinerary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(md_text)
    return fname


def ui():
    with gr.Blocks(title="AI Travel Buddy", fill_height=True) as demo:
        gr.Markdown("# 🧭 AI Travel Buddy")
        gr.Markdown(
            "Craft a personalized itinerary with a **quirk slider**. Perfect for demos: tweak vibe, pace, and budget. "
            "Set **dietary needs** and **avoid** list to keep suggestions on-point. "
            "*(No bookings; this is a planning assistant.)*"
        )

        with gr.Row():
            with gr.Column(scale=2):
                destination = gr.Textbox(label="Destination (city/region)", placeholder="e.g., Kyoto, Japan")
                days = gr.Slider(label="Trip Length (days)", minimum=1, maximum=21, step=1, value=5)
                month_hint = gr.Textbox(label="Month/Season (optional)", placeholder="e.g., April, or Oct 2025")

                budget_level = gr.Dropdown(
                    label="Budget Level",
                    choices=["shoestring", "moderate", "premium", "luxury"],
                    value="moderate"
                )
                pace = gr.Dropdown(
                    label="Pace",
                    choices=["relaxed", "balanced", "packed"],
                    value="balanced"
                )
                vibe = gr.Dropdown(
                    label="Vibe",
                    choices=["foodie", "outdoors", "culture", "nightlife", "family", "romantic", "mixed"],
                    value="mixed"
                )
                companions = gr.Dropdown(
                    label="Companions",
                    choices=["solo", "couple", "friends", "family", "business"],
                    value="solo"
                )
                dietary = gr.Dropdown(
                    label="Dietary Needs",
                    choices=["none", "vegetarian", "vegan", "halal", "kosher", "gluten-free", "other"],
                    value="none"
                )
                must_do = gr.Textbox(label="Must-Do (optional)", placeholder="e.g., tea ceremony, ramen, live jazz")
                avoid = gr.Textbox(label="Avoid (optional)", placeholder="e.g., long hikes, night buses")

                quirkiness = gr.Slider(label="Quirkiness", minimum=0, maximum=100, step=5, value=50)

                with gr.Accordion("Model Settings", open=False):
                    model = gr.Textbox(label="Model", value=DEFAULT_MODEL)
                    temperature = gr.Slider(label="Temperature", minimum=0.0, maximum=1.0, step=0.1, value=DEFAULT_TEMPERATURE)

                generate_btn = gr.Button("✨ Generate Itinerary", variant="primary")

                with gr.Row():
                    preset1 = gr.Button("Preset: Tokyo Foodie (5 days)")
                    preset2 = gr.Button("Preset: Lisbon Outdoors (4 days)")
                    preset3 = gr.Button("Preset: NYC Culture (3 days, Offbeat)")

            with gr.Column(scale=3):
                md_out = gr.Markdown(label="Itinerary", value="(Your itinerary will appear here)")
                json_out = gr.JSON(label="Raw JSON (debug/curious)")
                export_btn = gr.Button("⬇️ Export as Markdown")
                file_out = gr.File(label="Download")

        # Wiring
        generate_btn.click(
            plan_trip,
            inputs=[destination, days, budget_level, pace, vibe, companions, dietary, must_do, avoid, quirkiness, month_hint, model, temperature],
            outputs=[md_out, json_out]
        )

        export_btn.click(
            export_markdown,
            inputs=[md_out],
            outputs=[file_out]
        )

        # Presets
        def set_preset(name: str):
            if name == "tokyo":
                return ("Tokyo, Japan", 5, "moderate", "balanced", "foodie", "solo", "none",
                        "Tsukiji outer market; kissaten coffee; ramen; Japanese whisky bars",
                        "long bus rides", 40, "April", DEFAULT_MODEL, DEFAULT_TEMPERATURE)
            if name == "lisbon":
                return ("Lisbon, Portugal", 4, "moderate", "balanced", "outdoors", "couple", "vegetarian",
                        "Miradouros (viewpoints), tram 28, pastel de nata",
                        "crowded mega-malls", 30, "May", DEFAULT_MODEL, DEFAULT_TEMPERATURE)
            if name == "nyc":
                return ("New York City, USA", 3, "premium", "packed", "culture", "friends", "gluten-free",
                        "Off-Broadway theater, galleries, speakeasies",
                        "Times Square, chain restaurants", 80, "October", DEFAULT_MODEL, DEFAULT_TEMPERATURE)
            return ("", 5, "moderate", "balanced", "mixed", "solo", "none", "", "", 50, "", DEFAULT_MODEL, DEFAULT_TEMPERATURE)

        preset1.click(
            set_preset, inputs=[], outputs=[destination, days, budget_level, pace, vibe, companions, dietary, must_do, avoid, quirkiness, month_hint, model, temperature],
            api_name="preset_tokyo"
        )
        preset2.click(
            set_preset, inputs=[], outputs=[destination, days, budget_level, pace, vibe, companions, dietary, must_do, avoid, quirkiness, month_hint, model, temperature],
            api_name="preset_lisbon"
        )
        preset3.click(
            set_preset, inputs=[], outputs=[destination, days, budget_level, pace, vibe, companions, dietary, must_do, avoid, quirkiness, month_hint, model, temperature],
            api_name="preset_nyc"
        )

    return demo


if __name__ == "__main__":
    demo = ui()
    demo.launch()
