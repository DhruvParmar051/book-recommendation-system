# book-recommendation-system
 A robust data pipeline to extract, clean, and store book information (titles, descriptions, genres) to provide a high-quality dataset for an ML-powered semantic search system.

Plausible Repo structure :

book-recommendation-system/
├── api/
│   └── main.py
├── data/
│   ├── raw/
│   └── processed/
├── ingestion/
│   └── ingest.py
├── logs/
│   └── llm_usage.md
├── storage/
│   └── db.py
├── transformation/
│   └── clean.py
├── requirements.txt
└── README.md