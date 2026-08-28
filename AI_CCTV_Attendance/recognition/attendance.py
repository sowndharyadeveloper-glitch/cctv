from datetime import datetime


def calculate_attendance_status(current_time: str, start_time: str = "09:00", late_after: str = "09:15") -> str:
    try:
        current_dt = datetime.strptime(current_time, "%H:%M:%S")
    except ValueError:
        current_dt = datetime.strptime(current_time, "%H:%M")

    start_dt = datetime.strptime(start_time, "%H:%M")
    late_dt = datetime.strptime(late_after, "%H:%M")

    if current_dt <= start_dt:
        return "Present"
    if current_dt <= late_dt:
        return "Present"
    return "Late"
