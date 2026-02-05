# AI Operations Assistant

[![Try it Live](https://img.shields.io/badge/Try%20it-Live%20Demo-D97757?style=for-the-badge)](https://pieby2-ai-ops-app-mnt3ik.streamlit.app/)

A multi-agent AI system that accepts natural-language tasks, plans execution steps, calls APIs, and returns structured answers.

## Features

- **Multi-agent architecture** with Planner, Executor, and Verifier agents
- **LLM-powered reasoning** using Groq (Llama 3.3 70B)
- **Three API integrations**: GitHub, Weather (Open-Meteo), and NewsAPI
- **Parallel execution** for independent steps
- **Response caching** to reduce API costs
- **Token & cost tracking** per request
- **Long-term memory** for query history and user preferences
- **Streamlit UI** with dark theme

## Quick Start

### Prerequisites
- Python 3.8+
- Groq API key (free tier available)
- GitHub token (optional, for repo search)
- NewsAPI key (optional, for news search)

### Installation

```bash
cd ai_ops_assistant
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## 🔐 API Key Setup

> ⚠️ **Security Notice:** Always use your own API keys. Never share API keys publicly or commit them to version control.

### Required: Groq API Key

1. Visit **[https://console.groq.com/keys](https://console.groq.com/keys)**
2. Sign up or log in to your account
3. Click "Create API Key"
4. Copy your API key (starts with `gsk_`)

**Option A:** Add to `.env` file (recommended for local development):
```bash
GROQ_API_KEY=gsk_your_groq_api_key
```

**Option B:** Enter directly in the app's sidebar when running

### Optional: GitHub Token

For enhanced GitHub repository search:
1. Visit [GitHub Settings > Tokens](https://github.com/settings/tokens)
2. Generate a new token with `public_repo` scope
3. Add to `.env`:
```bash
GITHUB_TOKEN=ghp_your_github_token
```

### Optional: NewsAPI Key

For news article search:
1. Visit [https://newsapi.org](https://newsapi.org)
2. Sign up for a free account
3. Add to `.env`:
```bash
NEWS_API_KEY=your_newsapi_key
```

### Environment Variables Summary

```bash
# Required
GROQ_API_KEY=gsk_your_groq_api_key

# Optional
GITHUB_TOKEN=ghp_your_github_token
NEWS_API_KEY=your_newsapi_key
LLM_MODEL=llama-3.3-70b-versatile
```

## Usage

### Streamlit UI (Recommended)

```bash
streamlit run app.py
```

### CLI Mode

```bash
python cli.py "What's the weather in Tokyo?"
python cli.py --interactive
```

## Example Tasks

```
"What is the weather in London?"
"Find popular Python web frameworks on GitHub"
"Get the latest news about artificial intelligence"
"Get weather in Tokyo and find AI repositories"
```

## Project Structure

```
ai_ops_assistant/
├── agents/
│   ├── planner.py      # Task planning
│   ├── executor.py     # Step execution
│   └── verifier.py     # Result validation
├── tools/
│   ├── github_tool.py  # GitHub search
│   ├── weather_tool.py # Weather data
│   └── news_tool.py    # News search
├── llm/
│   └── provider.py     # Groq LLM client
├── app.py              # Streamlit UI
├── cli.py              # CLI interface
└── cache.py            # Response caching
```

## API Integrations

| Tool | Description |
|------|-------------|
| **GitHub** | Search repositories by topic |
| **Weather** | Get weather data for any city |
| **News** | Search latest news articles |

## License

MIT
