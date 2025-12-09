# WebScrapeX — AI Web Scraper & SEO Analyzer

ScraperLab is a modern, full-stack AI-powered web scraping and SEO intelligence platform.
It extracts article content, product details, pricing data, keywords, SEO metrics, and more — with AI summaries, SEO insights, and job history tracking.

Built using FastAPI, SQLModel, and Next.js with a sleek UI.

# Features
# Web Scraping Engine

1. Extract titles, paragraphs, article content

2. Auto-detect main content OR use custom CSS selector

3. Export structured results to CSV

4. Job history with refresh & delete options

5. Beautiful "Glass UI" cards

# Product Mode

1. Extract:

     a. Product Name

     b. Brand

     c. Price / MRP / Discount

     d. Rating & Review Count

2. Key Features

3. Automatic price normalization (₹, $, €, £, etc.)

# AI Enhancements

1. AI Summaries (OpenAI)

2. Fallback summary when no key available

3. AI rewrite (SEO tool)

4. AI suggestions for improvement

5. SEO Analyzer

6. Extract:

     a. Page Title

     b. Meta Description

     c. Headings H1–H6

     d. Top Keywords with density

     e. Readability metrics (Flesch score)

     f. SEO Suggestions

     g. AI rewrite (optional)

     h. SEO History tracking

# Tech Stack

# Frontend

1. Next.js

2. TailwindCSS

3. Axios

# Backend

1. Python

2. FastAPI

3. SQLModel + SQLite

4. OpenAI API

5. BeautifulSoup / Requests

# Dev Tools

1. Uvicorn

2. dotenv

3. CORS Middleware

# Project Structure

<img width="382" height="843" alt="image" src="https://github.com/user-attachments/assets/87360ca3-d9ac-48f2-8262-011aed70b83b" />


# Backend Setup (FastAPI)
# Create virtual environment
cd backend
python -m venv .venv
.venv/Scripts/activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
DATABASE_URL=sqlite:///./scrapes.db
OPENAI_API_KEY=your_openai_key_here
SCRAPE_OUTPUT_DIR=./backend/app/outputs

# Start server
uvicorn app.main:app --reload

# Frontend Setup (Next.js)
1️. Install dependencies
cd frontend
npm install

2️. Add .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000

3️. Run development server
npm run dev
