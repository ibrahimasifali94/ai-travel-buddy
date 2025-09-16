# 🧭 AI Travel Buddy

A **low-code**, **recruiter-playable** Gradio web app that crafts quirky or classic travel itineraries.
Perfect as a portfolio piece — deploy it in minutes and let interviewers try it live.

---

## ✨ Features
- **Quirk slider** to dial recommendations from *safe* → *offbeat*.
- **Personalization** by budget, pace, vibe, dietary needs, must/avoid, companions.
- **Structured output** (JSON) → rendered into clean Markdown itinerary.
- **One-click export**: download Markdown itinerary.
- **Presets** for quick demos (e.g., "Tokyo foodie, 5 days").
- **Low code**: single-file app (`app.py`) + Gradio UI + OpenAI API.

---

## 🛠️ Tech
- **Frontend/Hosting**: [Gradio](https://www.gradio.app/) (works locally or on Hugging Face Spaces)
- **LLM**: OpenAI Chat Completions (change model via `.env`)
- **Env management**: `python-dotenv`

> You can swap the LLM provider with minimal changes in `app.py` (see comments).

---

## 🚀 Quickstart (Local)

1. **Clone** the repo or unzip the files.
2. Create a virtual env (recommended):
   ```bash
   python -m venv .venv && source .venv/bin/activate   # on macOS/Linux
   # or: .venv\Scripts\activate                      # on Windows
   ```
3. **Install deps**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Create `.env`** from template:
   ```bash
   cp .env.example .env
   # then open .env and paste your OpenAI API key
   ```
5. **Run the app**:
   ```bash
   python app.py
   ```
6. Open the local URL Gradio prints (something like `http://127.0.0.1:7860`).

---

## ☁️ Deploy to Hugging Face Spaces (free)

1. Create a new **Space** → **Gradio** template.
2. Upload these files (`app.py`, `requirements.txt`, `.env.example`, `README.md`).
3. Add a **Secret** named `OPENAI_API_KEY` (Settings → Variables & secrets → New secret).
4. (Optional) Add `OPENAI_MODEL` and `OPENAI_TEMPERATURE` secrets to customize defaults.
5. Hit **Rebuild** — your app will be live at a sharable URL.

> Spaces automatically installs `requirements.txt`. The app reads your API key from the environment, so you don't need to upload a `.env` file in public.

---

## 🧩 What to Show in Interviews

- **Live demo**: drag the quirk slider, switch vibes (“foodie”, “outdoors”), toggle pace.
- **Presets**: use the pre-filled examples to go from zero to plan in seconds.
- **Explain the prompt design**: safety rails + JSON schema + personalization controls.
- **Show code**: small, readable, well-commented. Easy to extend.

---

## 🔧 Customize
- Change the prompt or the JSON schema in `build_prompt()`.
- Add image cards / maps by post-processing the JSON (e.g., fetch POI images).
- Swap the LLM: replace the OpenAI call with another provider (e.g., Anthropic, OpenRouter, Groq).

---

## ⚠️ Notes
- This app **does not** book travel or fetch real-time prices. It creates **personalized itineraries** with a fun/quirky angle.
- Be mindful of API costs; set a reasonable temperature and max tokens.

---

## 📝 License
MIT — use freely in your portfolio.
