# 📚 Book Recommendation System  
## End-to-End Data Engineering Pipeline

This project implements a **modular, multi-stage data pipeline** for building a Book Recommendation System.  
The system is designed using **data engineering best practices**, where each stage of processing is isolated into a dedicated phase and executed in a controlled sequence.

The entire pipeline is orchestrated through a single entry point (`main.py`), ensuring reproducibility, fault isolation, and clear separation of responsibilities.

---

## 🎯 Project Objective

The primary goal of this project is to convert **raw, unstructured, and incomplete book metadata** into a **clean, enriched, and query-ready dataset** that can be used for:

- Book recommendation systems
- Search and retrieval
- Downstream machine learning models
- Academic analysis

---

## 🏗️ Pipeline Overview

The pipeline consists of **four major phases**, executed sequentially:

1. **Ingestion**
2. **Cleaning**
3. **Transformation (OPAC Enrichment)**
4. **Storage (JSON → SQLite)**

Each phase is implemented as an **independent Python module** and executed using a subprocess-based orchestration mechanism.

---

## 🟡 Phase 1: Ingestion

### Purpose

The ingestion phase is responsible for **reading raw source data** and bringing it into a controlled internal format.

### Responsibilities

- Read raw CSV files from the data source
- Handle encoding inconsistencies safely
- Standardize column names into a canonical schema
- Ensure all expected fields exist
- Perform minimal type normalization (without cleaning)

### Design Principle

Ingestion focuses on **structure, not correctness**.  
No semantic cleaning or deduplication is performed at this stage.

---

## 🟠 Phase 2: Cleaning

### Purpose

The cleaning phase improves **data quality** while preserving the original meaning of the records.

### Responsibilities

- Normalize textual fields (titles, authors, publishers)
- Remove noise such as extra whitespace and inconsistent casing
- Handle missing or malformed values
- Prepare data for reliable transformation and enrichment

### Design Principle

Cleaning is intentionally separated from ingestion to:

- Avoid accidental data loss
- Enable easier debugging
- Allow re-cleaning without re-ingesting raw data

---

## 🔵 Phase 3: Transformation (OPAC Enrichment)

### Purpose
The transformation phase enriches the cleaned data using **external library metadata sources**, such as OPAC or catalog systems.

### Responsibilities
- Enrich book records with additional metadata
- Merge multiple data sources into a unified representation
- Resolve structural inconsistencies after enrichment
- Prepare records for long-term storage

### Design Principle
Transformation focuses on **enhancement**, not validation.  
Any enrichment failures are handled gracefully to keep the pipeline resilient.


---

## 🔴 Phase 4: Storage (JSON → SQLite)

### Purpose
The storage phase persists the final processed dataset into a **relational database**.

### Responsibilities
- Convert processed data into a structured SQLite database
- Create a query-ready storage layer
- Enable fast access for search and recommendation systems

### Design Principle
SQLite is chosen for:
- Lightweight deployment
- No external server requirement
- Easy migration to production databases later

---

## ⚙️ Pipeline Orchestration

The pipeline is orchestrated using a **central controller script** (`main.py`), which:

- Executes each phase in strict order
- Uses subprocess isolation for each stage
- Stops execution immediately on failure
- Provides clear logging for each pipeline step

This orchestration ensures:
- No phase runs with incomplete data
- Errors are localized and easy to diagnose
- The pipeline can be re-run safely

---

## 📁 Logical Project Structure

The project follows a clean, phase-oriented structure:

- Ingestion module for raw data intake
- Cleaning module for data quality improvement
- Transformation module for enrichment
- Storage module for persistence
- Central orchestrator for execution control

This structure mirrors **real-world ETL pipelines** used in production systems.

---

## 🎓 Academic Perspective

This project demonstrates:
- Proper separation of concerns
- Industry-aligned data engineering workflow
- Safe pipeline orchestration
- Thoughtful handling of real-world messy data

It clearly distinguishes between **ingestion**, **cleaning**, and **transformation**, which is a key expectation in Big Data Engineering evaluations.
---

## 🚀 Future Enhancements

- Recommendation algorithms (content-based / collaborative filtering)
- REST API for serving recommendations
- Full-text search support
- Logging and monitoring
- Dockerized deployment
- Migration to PostgreSQL or distributed storage

---

## 🏁 Final Outcome

The Book Recommendation System pipeline successfully transforms raw book records into a **clean, enriched, and persistent dataset**.  
It forms a strong foundation for intelligent recommendation systems and scalable data-driven applications.
