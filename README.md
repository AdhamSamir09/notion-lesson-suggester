# 📊 Intelligent Study Planner (Notion + Optimization Engine)

An automated study planning system that integrates with Notion to generate **daily lesson recommendations** based on urgency, workload constraints, and optimization techniques.

This is not a basic task sorter. It is a **decision-making system** that models time as a constrained resource and solves a selection problem using **Mixed Integer Linear Programming (MILP)**.

---

## 🚀 Core Idea

Most study planners fail because they:
- Treat all tasks equally
- Ignore time constraints
- Don’t adapt to deadlines dynamically

This system fixes that by:
1. Assigning **dynamic urgency scores** to lessons
2. Accounting for **real daily availability**
3. Solving a **constrained optimization problem** to select the best lessons

---

## ⚙️ Features

### 1. 📥 Notion Integration
- Fetches:
  - Lessons (name, subject, difficulty, due week, credit, status)
  - Tasks (due date, duration)
- Updates:
  - Suggestions database (daily recommendations)

---

### 2. ⏱ Time Modeling
- Daily available time depends on weekday:
  - Weekdays → 6 hours
  - Weekends → 12 hours
- Subtracts time already consumed by tasks due today

---

### 3. 📈 Urgency Algorithm

Each lesson gets a score based on:
- Deadline proximity
- Progress status
- Lesson weight (credit)

#### Behavior:
- Far deadlines → low urgency
- Near deadlines → sharply increasing urgency
- Overdue lessons → heavily penalized (forced priority)

---

### 4. 🧠 Optimization Engine (MILP)

The system formulates lesson selection as:

> Maximize total urgency under a time constraint

#### Formulation:

- Decision variable:
  - `x_i ∈ {0,1}` → whether lesson *i* is selected

- Objective:
```
maximize: sum(urgency_i * x_i)
```

- Constraint:
```
sum(time_i * x_i) ≤ available_time
```

Solved using:
```python
scipy.optimize.milp
```

This is equivalent to a **Knapsack Problem**, solved optimally.

---

### 5. 🔄 Automatic Suggestion Refresh
- Deletes old suggestions
- Uploads new optimized plan daily
- Ensures recommendations are always relevant

---

## 🏗 Architecture Overview

```
Notion API
   │
   ├── Lessons Data → Processing → Urgency Scoring
   │
   ├── Tasks Data → Time Adjustment
   │
   ▼
Optimization Engine (MILP)
   │
   ▼
Selected Lessons
   │
   ▼
Notion Suggestions Database
```

---

## 📂 Project Structure

```
script.py
│
├── Configuration (API keys, DB IDs)
├── Data Fetching
│   ├── get_lesson_data()
│   └── get_tasks_data()
│
├── Processing
│   ├── urgency_algorithm()
│   └── available_time()
│
├── Optimization
│   └── suggestions_choice()
│
├── Output
│   ├── delete_all_suggestions()
│   └── suggestion_upload()
│
└── main()
```

---

## 🔧 Setup

### 1. Install dependencies
```bash
pip install notion-client numpy scipy
```

---

### 2. Configure Notion
Replace:

```python
INTEGRATION_TOKEN = "your_token"
LESSONS_DATABASE_ID = "your_lessons_db"
SUGGESTIONS_DB_ID = "your_suggestions_db"
TASKS_DB_ID = "your_tasks_db"
```

---

### 3. Run the script
```bash
python script.py
```

---

## 📊 Example Workflow

1. Fetch lessons from Notion  
2. Compute urgency scores  
3. Calculate available time  
4. Subtract today's tasks  
5. Run MILP optimizer  
6. Select best lessons  
7. Upload suggestions  

---

## ⚠️ Limitations

- Assumes fixed time estimates (based on difficulty)
- Urgency function is heuristic (not learned)
- No user feedback loop yet
- Single-day optimization (no multi-day planning)

---

## 🔮 Future Improvements

- Machine learning-based urgency prediction
- Adaptive time estimation per user
- Multi-day planning (rolling horizon optimization)
- Reinforcement learning for scheduling policies

---
