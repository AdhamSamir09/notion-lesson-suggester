from datetime import datetime, date
from notion_client import Client
from notion_client.errors import APIResponseError
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

# --- Configuration ---
INTEGRATION_TOKEN = "Enter Token"
LESSONS_DATABASE_ID = "Enter ID"
SUGGESTIONS_DB_ID = "Enter ID"
TASKS_DB_ID = "Enter ID"

notion = Client(auth=INTEGRATION_TOKEN)

SEMESTER_START = date(2026, 2, 7)
today = date.today()
days_passed = (today - SEMESTER_START).days

DEFAULT_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/4/47/Placeholder.png"

def parse_date(date_str): 
    """
    Safely converts Notion's date strings into Python date objects.
    Handles both full ISO timestamps and simple YYYY-MM-DD formats.
    """
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str).date()
    except (ValueError, AttributeError):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None 

def available_time():
    """
    Determines the total study hours available for the current day.
    Provides a higher budget (12h) for Thu/Fri/Sat and lower (6h) for others.
    """
    week_day = today.weekday() # Monday=0, Sunday=6
    if 0 <= week_day <= 2 or week_day == 6: 
        return 6
    elif 3 <= week_day <= 5: 
        return 12
    return 0

def get_lesson_data():
    """
    Fetches all academic lessons from Notion and maps Difficulty 
    labels to specific estimated study durations (in hours).
    """
    try:
        response = notion.databases.query(database_id=LESSONS_DATABASE_ID)
        lessons = []
        for item in response["results"]:
            properties = item["properties"]

            name = properties.get("Name", {}).get("title", [])
            name_text = name[0]["text"]["content"] if name else "Untitled"
            status = properties.get("Status", {}).get("status", {}).get("name", "Unknown")
            subject_name = properties.get("Subject", {}).get("select", {}).get("name", "Unknown")
            week_number = properties.get("Due Week", {}).get("number") or 1
            credit = properties.get("Credit", {}).get("number") or 1
            
            difficulty_name = properties.get("Difficulty", {}).get("select", {}).get("name", "Unknown")
            
            if difficulty_name == "Easy":
                estimated_time = 2
            elif difficulty_name == "Medium":
                estimated_time = 4 
            elif difficulty_name == "Hard":
                estimated_time = 6
            else:
                estimated_time = 1.5

            lessons.append({
                "Name": name_text,
                "Subject": subject_name,
                "Status": status,
                "Due Week": week_number,
                "Difficulty": difficulty_name,
                "Estimated Time": estimated_time,
                "Credit": credit
            })
        return lessons
    except Exception as e:
        print(f"Error fetching lessons: {e}")
        return []

def get_tasks_data():
    """
    Retrieves incomplete tasks from the Tasks database to calculate
    how much of today's time budget is already committed.
    """
    try:
        response = notion.databases.query(database_id=TASKS_DB_ID)
        tasks = []
        for item in response["results"]:
            properties = item["properties"]
            status_bol = properties.get("Status", {}).get("checkbox")
            
            if status_bol == False:
                date_obj = properties.get("Due Date", {}).get("date")
                task_date = parse_date(date_obj.get("start")) if date_obj else None
                estimated_duration = properties.get("Estimated Duration (h)", {}).get("number") or 0
                
                tasks.append({
                    "Status": status_bol,
                    "Due Date": task_date,
                    "Estimated Duration": estimated_duration,
                })
        return tasks
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []

def urgency_algorithm(lessons):
    """
    Assigns a numerical priority score to each lesson based on how 
    soon it is due, its current status, and its credit weight.
    """
    scored_lessons = lessons
    for lesson in scored_lessons:
        status = lesson["Status"]
        credit = lesson["Credit"]
        due_week = lesson["Due Week"]
        days_left = (due_week * 7) - days_passed
        
        if status == "Completed": 
            urgency = 0
        elif days_left > 8:
            urgency = credit
        elif 8 >= days_left >= 0 and status == "Not Started":
            urgency = credit * (1 + 1.5 * (5 / (days_left + 1)))
        elif days_left > 0 and status == "Ongoing":
            urgency = credit * (1 + 1.5 * (2 / days_left))
        elif days_left < 0:
            urgency = credit * (1 + 3 * abs(days_left))
        else:
            urgency = 0

        lesson["Urgency"] = round(urgency, 2)

    scored_lessons.sort(key=lambda x: x["Urgency"], reverse=True)
    return scored_lessons

def suggestions_choice(daily_time, scored_lessons):
    """
    Uses Mixed-Integer Linear Programming (MILP) to select the optimal set 
    of lessons that fits within the remaining time budget for the day.
    """
    all_tasks = get_tasks_data()
    today_tasks = [task for task in all_tasks if task["Due Date"] == today]
    total_time_consumed = sum(task.get("Estimated Duration") or 0 for task in today_tasks)
    time_left = daily_time - total_time_consumed

    if time_left <= 0:
            print("🚨 Schedule Full: Today's tasks consume all available time.")
            return []

    valid_lessons = [lesson for lesson in scored_lessons if lesson["Status"] != "Completed"]
    if not valid_lessons: return []

    urgencies = np.array([lesson.get("Urgency", 0) for lesson in valid_lessons])
    durations = np.array([lesson.get("Estimated Time") for lesson in valid_lessons])

    # MILP maximizes by minimizing the negative urgency
    result = milp(
        c=-urgencies, 
        constraints=LinearConstraint(np.array([durations]), lb=0, ub=time_left), 
        integrality=np.ones_like(urgencies), 
        bounds=Bounds(0, 1)
    )

    final_selection = []
    if result.success:
        for index, was_chosen in enumerate(np.round(result.x)):
            if was_chosen == 1.0:
                final_selection.append(valid_lessons[index])
    return final_selection

def delete_all_suggestions():
    """
    Clears the Suggestions database in Notion to make room for 
    the fresh calculation of daily priorities.
    """
    try:
        old_suggestions = notion.databases.query(database_id=SUGGESTIONS_DB_ID)
        for lesson in old_suggestions["results"]:
            notion.blocks.delete(block_id=lesson["id"])
        print("Old suggestions deleted.")
    except Exception as e:
        print(f"Failed to delete old suggestions: {e}")

def suggestion_upload(lesson):
    """
    Creates a new page in the Notion Suggestions database for a specific lesson.
    """
    try:
        notion.pages.create(
            parent={"database_id": SUGGESTIONS_DB_ID},
            properties={
                "Name": {"title": [{"text": {"content": lesson["Name"]}}]}
            },
            children=[
                {"object": "block", "type": "embed", "embed": {"url": DEFAULT_IMAGE}}
            ]
        )
        print(f"Suggestion added: {lesson['Name']}")
    except Exception as e:
        print(f"Error adding suggestion: {e}")

def main():
    """
    The orchestrator: runs the budget check, data fetch, 
    urgency calculation, and final upload process.
    """
    total_capacity = available_time()
    lessons = get_lesson_data()
    if not lessons: return

    scored = urgency_algorithm(lessons)
    plan = suggestions_choice(total_capacity, scored)
    
    delete_all_suggestions()

    if plan:
        print(f"Suggestions found for {len(plan)} lessons.")
        for item in plan:
            suggestion_upload(item)
    else:
        print("No room for new lessons today.")

if __name__ == "__main__":
    main()