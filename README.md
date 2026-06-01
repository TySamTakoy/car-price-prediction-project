# Car Price Prediction Project

A full-stack application for predicting car prices using machine learning and computer vision. Upload a car photo and enter basic parameters — the system returns an estimated market price.

## Architecture

```
car-price-prediction-project/
├── python-services/       # ML model service + computer vision service (Python)
├── springboot-backend/    # REST API gateway and business logic (Java / Spring Boot)
├── react-ts-frontend/     # User interface (React + TypeScript)
└── docker/                # Docker Compose and deployment configuration
```

### How the services interact

```
Browser
  │
  ▼
React TypeScript Frontend  (port 3000)
  │
  ▼
Spring Boot Backend        (port 8080)   ←── orchestrates requests
  ├──▶ ML Prediction Service  (port 5001)   ←── predicts price from features
  └──▶ CV Analysis Service    (port 5002)   ←── extracts car features from photo
```

## Quick Start (Docker Compose)

**Prerequisites:** Docker ≥ 20.x and Docker Compose ≥ 2.x installed.

```bash
# Clone the repository
git clone https://github.com/TySamTakoy/car-price-prediction-project.git
cd car-price-prediction-project

# Build and start all services
cd docker
docker compose up --build
```

Once running, open your browser at **http://localhost:3000**.

To stop all services:
```bash
docker compose down
```

## Local Development (without Docker)

Start each service individually — see the README in each subfolder for detailed instructions:

| Service | Stack | Port | README |
|---------|-------|------|--------|
| ML / CV Python services | Python 3.10+ | 5001, 5002 | [python-services/README.md](./python-services/README.md) |
| Backend API | Java 17 / Spring Boot 3 | 8080 | [springboot-backend/README.md](./springboot-backend/README.md) |
| Frontend | Node 18+ / React + TypeScript | 3000 | [react-ts-frontend/README.md](./react-ts-frontend/README.md) |
| Docker setup | Docker Compose | — | [docker/README.md](./docker/README.md) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Vite |
| Backend API | Java 17, Spring Boot 3, Maven |
| ML Service | Python 3.10, scikit-learn, FastAPI |
| CV Service | Python 3.10, OpenCV / PIL, FastAPI |
| Containerisation | Docker, Docker Compose |

## Features

- **Photo-based prediction** — upload a car image; computer vision extracts make/model hints automatically.
- **Form-based prediction** — enter mileage, year, fuel type, transmission, and other parameters directly.
- **REST API** — all prediction logic is exposed via a documented JSON API.
- **Containerised** — the entire stack runs with a single `docker compose up`.

## License

This project is licensed under the [GPL-2.0 License](./LICENSE).
