# Vibber - AI Agent Cloning Platform

<p align="center">
  <strong>Create AI clones of yourself to handle routine tasks across Slack, GitHub, Jira, and more.</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#development">Development</a> •
  <a href="#deployment">Deployment</a>
</p>

---

## Overview

Vibber enables employees to create AI agent clones of themselves that can autonomously handle routine tasks across multiple enterprise platforms. The platform provides a dashboard for monitoring agent interactions and handling escalations when human judgment is needed.

**Price:** $20/user/month

## Features

### Core Capabilities

- **AI Agent Clone** - Creates a personalized AI that matches your communication style and domain knowledge
- **Multi-Platform Integration** - Connects to Slack, GitHub, Jira, Confluence, Elasticsearch, and more
- **Intelligent Escalation** - Automatically escalates uncertain decisions to humans
- **Confidence Scoring** - Transparent confidence levels for all agent actions
- **Training Interface** - Easy feedback loop to continuously improve agent performance

### Ralph Wiggum Iterative Task Execution

Vibber includes **Ralph Wiggum**, an autonomous AI coding agent that iterates on tasks until completion. Named after the Simpsons character who never stops trying, Ralph uses a simple but powerful technique:

**How it works:**
1. Submit a task description (e.g., "Fix the authentication bug in auth.py")
2. Ralph iterates on the task, seeing previous work via git history and modified files
3. Backpressure from tests, linting, and type checking validates each iteration
4. Agent continues until a completion signal is detected or max iterations reached

**Key Features:**
- **Iterative Improvement** - Learns from mistakes and previous iterations
- **Backpressure Validation** - Automatic test, lint, and typecheck runs
- **Completion Detection** - Flexible completion signals and semantic analysis
- **Tool Access** - File operations, shell commands, git integration
- **Configurable** - Custom test commands, max iterations, and completion promises

**API Usage:**
```bash
# Create a task (async)
POST /api/v1/ralph/tasks
{
  "prompt": "Add input validation to the user registration form",
  "max_iterations": 20,
  "run_tests": true
}

# Create and wait for completion (sync)
POST /api/v1/ralph/tasks/sync?timeout=600
{
  "prompt": "Fix the failing test in test_auth.py"
}

# Check task status
GET /api/v1/ralph/tasks/{taskId}

# Cancel a running task
POST /api/v1/ralph/tasks/{taskId}/cancel
```

### Supported Integrations

| Platform | Capabilities |
|----------|--------------|
| **Slack** | Auto-reply to DMs, handle @mentions, thread responses, emoji reactions |
| **GitHub** | PR reviews, code comments, issue triage, label management |
| **Jira** | Ticket updates, status changes, comment replies, assignment |
| **Confluence** | Knowledge search, page updates, comment management |
| **Elasticsearch** | Log monitoring, error detection, alert creation, RCA analysis |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend development)
- Go 1.22+ (for local backend development)
- Python 3.11+ (for local AI agent development)

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/vibber.git
cd vibber

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: ANTHROPIC_API_KEY, OPENAI_API_KEY
```

### Running with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Access Points

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8080
- **AI Agent API:** http://localhost:8000
- **RabbitMQ Management:** http://localhost:15672 (guest/guest)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VIBBER ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                    │
│  │   React     │────▶│   Go API    │────▶│   Python    │                    │
│  │  Frontend   │     │   Backend   │     │  AI Agent   │                    │
│  └─────────────┘     └─────────────┘     └─────────────┘                    │
│         │                   │                   │                           │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────────────────────────────────────────────┐                    │
│  │              PostgreSQL + pgvector                   │                    │
│  │                    Redis                             │                    │
│  │                  RabbitMQ                            │                    │
│  └─────────────────────────────────────────────────────┘                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 19, Tailwind, Zustand | User interface |
| Backend | Go, Chi Router, pgx | REST API, webhooks |
| AI Agent | Python, FastAPI, LangChain | AI processing |
| Database | PostgreSQL + pgvector | Data persistence |
| Cache | Redis | Session, rate limiting |
| Queue | RabbitMQ | Async processing |
| LLM | Claude 3.5 Sonnet | AI reasoning |
| Embeddings | OpenAI text-embedding-3 | Semantic search |

## Development

### Project Structure

```
vibber/
├── src/                    # React frontend
│   ├── components/         # UI components
│   ├── store/              # Zustand stores
│   ├── services/           # API clients
│   └── hooks/              # Custom hooks
├── backend/                # Go backend
│   ├── cmd/api/            # Application entry
│   ├── internal/           # Internal packages
│   │   ├── handlers/       # HTTP handlers
│   │   ├── models/         # Data models
│   │   ├── repository/     # Database access
│   │   └── middleware/     # HTTP middleware
│   └── migrations/         # SQL migrations
├── ai-agent/               # Python AI service
│   └── src/
│       ├── core/           # Agent core logic
│       ├── ralph/          # Ralph Wiggum iterative agent
│       ├── tools/          # Integration tools
│       ├── embeddings/     # Vector operations
│       └── memory/         # State management
└── docs/                   # Documentation
```

### Running Locally

**Frontend:**
```bash
npm install
npm start
```

**Backend:**
```bash
cd backend
go mod download
go run cmd/api/main.go
```

**AI Agent:**
```bash
cd ai-agent
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## API Reference

### Authentication

```bash
# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}

# Response
{
  "user": {...},
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "expiresIn": 900
}
```

### Agents

```bash
# List agents
GET /api/v1/agents

# Create agent
POST /api/v1/agents
{
  "name": "My AI Clone",
  "confidenceThreshold": 70
}

# Get agent status
GET /api/v1/agents/:id/status
```

### Interactions

```bash
# List interactions
GET /api/v1/interactions?page=1&page_size=20

# Submit feedback
POST /api/v1/interactions/:id/feedback
{
  "feedback": "approved|rejected|corrected",
  "correction": "optional correction text"
}
```

## Deployment

### Production Checklist

- [ ] Set secure `JWT_SECRET`
- [ ] Configure production database
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup strategy
- [ ] Set up log aggregation

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with care by the Vibber Team
</p>
