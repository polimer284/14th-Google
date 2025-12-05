import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import random

# Page configuration
st.set_page_config(
    page_title="Time Reservation Management System",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
:root {
    --primary-color: #4a90e2;
    --secondary-color: #2c3e50;
    --danger-color: #e74c3c;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --background-color: #f5f5f5;
}

.stApp {
    background-color: var(--background-color);
}

.metric-card {
    background-color: white;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
    text-align: center;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 5px;
}

.legend-color {
    width: 20px;
    height: 20px;
    border-radius: 3px;
    border: 1px solid #ccc;
}

h1, h2, h3 {
    color: var(--secondary-color);
}
</style>
""", unsafe_allow_html=True)

# Location capacity settings
LOCATION_CAPS = {
    "Denver": 40,
    "Tampa": 10,
    "San Francisco": 2,
    # Default cap for other locations
    "default": 3
}

def get_location_cap(location):
    """Get capacity cap for a location"""
    return LOCATION_CAPS.get(location, LOCATION_CAPS["default"])

# Updated sample data with multiple locations
def generate_sample_data():
    locations = ["Denver", "New York", "Los Angeles", "Chicago", "Boston"]
    sample_times = [
        "5:30 PM", "9:30 AM", "2:48 PM", "5:30 PM", "2:48 PM", "4:25 PM", 
        "9:40 AM", "10:00 AM", "9:44 AM", "3:45 PM", "4:30 PM", "9:49 AM",
        "8:00 AM", "4:50 PM", "10:20 AM", "10:56 AM", "6:33 AM", "12:00 PM"
    ]
    sample_dates = ["9/28/25", "9/29/25", "9/30/25"]
    
    data = []
    # Generate data for multiple locations
    for location in locations:
        num_records = 40 if location == "Denver" else random.randint(15, 35)
        for i in range(num_records):
            date = random.choice(sample_dates)
            time = sample_times[i % len(sample_times)]
            data.append({
                'location': location,
                'id': int(4.2e8 + random.randint(0, int(2e9))),
                'datetime': f"{date} {time}"
            })
    
    return data

DEFAULT_DATA = generate_sample_data()

def parse_datetime(datetime_str):
    """Parse datetime string in format 'M/D/YY H:MM AM/PM' and return datetime object"""
    try:
        return datetime.strptime(datetime_str, "%m/%d/%y %I:%M %p")
    except:
        try:
            return datetime.strptime(datetime_str, "%m/%d/%Y %I:%M %p")
        except:
            return None

def extract_time_only(datetime_str):
    """Extract time in HH:MM format from datetime string"""
    dt = parse_datetime(datetime_str)
    if dt:
        return dt.strftime("%H:%M")
    return "00:00"

def extract_date_only(datetime_str):
    """Extract date in M/D format from datetime string"""
    dt = parse_datetime(datetime_str)
    if dt:
        # Windows compatible format
        return f"{dt.month}/{dt.day}"
    return ""

def get_day_of_week(datetime_str):
    """Get day of week abbreviation (Mo, Tu, We, etc.)"""
    dt = parse_datetime(datetime_str)
    if dt:
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        return days[dt.weekday()]
    return ""

def extract_full_date(datetime_str):
    """Extract full date for sorting"""
    dt = parse_datetime(datetime_str)
    return dt if dt else datetime.min

def time_to_minutes(time_str):
    """Convert time string to minutes"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except:
        return 0

def minutes_to_time(minutes):
    """Convert minutes to time string"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def sort_reservations_by_time(data):
    """Sort reservations by time"""
    return sorted(data, key=lambda x: time_to_minutes(x['time']))

def calculate_time_slots(data, start_hour=8, end_hour=18, selected_location_date=None):
    """Calculate reservation status by time slots"""
    # Filter by location+date if selected
    if selected_location_date and selected_location_date != "All Dates":
        data = [item for item in data if item['location_date'] == selected_location_date]
    
    # Create 10-minute interval time slots
    time_slots = []
    for hour in range(start_hour, end_hour):
        for minute in range(0, 60, 10):
            slot_minutes = hour * 60 + minute
            time_slots.append({
                'time': minutes_to_time(slot_minutes),
                'minutes': slot_minutes,
                'count': 0,
                'reservations': []
            })
    
    # Filter reservations that have any overlap with the time range
    start_minutes = start_hour * 60
    end_minutes = end_hour * 60
    
    filtered_data = []
    for item in data:
        reservation_minutes = time_to_minutes(item['time'])
        reservation_start = reservation_minutes - 30
        reservation_end = reservation_minutes + 30
        
        if reservation_end > start_minutes and reservation_start < end_minutes:
            filtered_data.append(item)
    
    # Calculate slot occupancy for filtered reservations
    for item in filtered_data:
        original_minutes = time_to_minutes(item['time'])
        start_minutes_res = original_minutes - 30
        end_minutes_res = original_minutes + 30
        
        for slot in time_slots:
            slot_minutes = slot['minutes']
            if start_minutes_res <= slot_minutes < end_minutes_res:
                slot['count'] += 1
                slot['reservations'].append({
                    'id': item['id'],
                    'location_date': item['location_date'],
                    'time': item['time']
                })
    
    return time_slots, filtered_data

def calculate_max_overlap_per_location_date(data, start_hour=8, end_hour=18):
    """Calculate maximum overlap for each location-date separately"""
    # Group data by location_date
    location_date_groups = {}
    for item in data:
        location_date = item['location_date']
        if location_date not in location_date_groups:
            location_date_groups[location_date] = []
        location_date_groups[location_date].append(item)
    
    max_overlaps = {}
    
    # Calculate max overlap for each location-date
    for location_date, location_date_data in location_date_groups.items():
        # Create time slots for this location-date only
        time_slots, _ = calculate_time_slots(location_date_data, start_hour, end_hour)
        
        # Find maximum overlap for this location-date
        max_overlap = max([slot['count'] for slot in time_slots]) if time_slots else 0
        max_overlaps[location_date] = max_overlap
    
    # Return the overall maximum across all location-dates
    return max(max_overlaps.values()) if max_overlaps else 0

def analyze_busiest_hours(data, start_hour=8, end_hour=18):
    """Analyze busiest 1-hour time slots"""
    # Create time slots
    time_slots, _ = calculate_time_slots(data, start_hour, end_hour)
    
    # Group by 1-hour intervals (6 slots = 60 minutes)
    hourly_stats = {}
    
    for i in range(0, len(time_slots), 6):  # Every 6 slots = 1 hour
        hour_slots = time_slots[i:i+6]
        if not hour_slots:
            continue
            
        start_time = hour_slots[0]['time']
        # Calculate end time (1 hour later)
        start_minutes = time_to_minutes(start_time)
        end_minutes = start_minutes + 60
        end_time = minutes_to_time(end_minutes)
        
        # Calculate total overlaps in this hour
        total_overlap = sum(slot['count'] for slot in hour_slots)
        max_overlap = max(slot['count'] for slot in hour_slots) if hour_slots else 0
        
        # Count how many 10-min slots are "busy" (have overlaps)
        busy_slots = sum(1 for slot in hour_slots if slot['count'] > 0)
        
        hourly_stats[f"{start_time} - {end_time}"] = {
            'total_overlap': total_overlap,
            'max_overlap': max_overlap,
            'busy_slots': busy_slots,
            'start_time': start_time
        }
    
    # Sort by total overlap (descending) and get top 4
    sorted_hours = sorted(hourly_stats.items(), 
                         key=lambda x: (x[1]['total_overlap'], x[1]['max_overlap']), 
                         reverse=True)
    
    return sorted_hours[:4]

def create_heatmap(time_slots, data, selected_location_date=None, selected_location=None):
    """Create heatmap chart grouped by location-date with expandable details"""
    # Get location cap
    location_cap = get_location_cap(selected_location) if selected_location else LOCATION_CAPS["default"]
    
    # Prepare time-based data
    times = [slot['time'] for slot in time_slots]
    
    # Group data by location_date
    location_date_groups = {}
    for item in data:
        location_date = item['location_date']
        if location_date not in location_date_groups:
            location_date_groups[location_date] = []
        location_date_groups[location_date].append(item)
    
    # Sort location-dates by date (earliest first)
    sorted_location_dates = sorted(location_date_groups.keys(), 
                                   key=lambda ld: extract_full_date(location_date_groups[ld][0]['datetime']))
    
    # Create summary heatmap (only totals)
    z_data_summary = []
    y_labels_summary = []
    
    # **NEW: Calculate average row for each time slot**
    num_dates = len(sorted_location_dates)
    average_row = [0] * len(time_slots)
    
# Process each location-date - only totals (reversed to show earliest at top)
    for location_date in reversed(sorted_location_dates):
        location_date_items = location_date_groups[location_date]
        
        # Get day of week from first item in this location_date group
        day_of_week = location_date_items[0].get('day_of_week', '')
        
        # Calculate location-date total row
        location_date_total_row = [0] * len(time_slots)
        for item in location_date_items:
            original_minutes = time_to_minutes(item['time'])
            start_minutes = original_minutes - 30
            end_minutes = original_minutes + 30
            
            for i, slot in enumerate(time_slots):
                slot_minutes = slot['minutes']
                if start_minutes <= slot_minutes < end_minutes:
                    location_date_total_row[i] += 1
        
        # **NEW: Add to average calculation**
        for i in range(len(time_slots)):
            average_row[i] += location_date_total_row[i]
        
        # Add location-date total row with date and day of week
        z_data_summary.append(location_date_total_row)
        y_labels_summary.append(f"📅 {location_date} ({day_of_week})")
    
    # **NEW: Calculate final average and add as first row (정수로 변환)**
    if num_dates > 0:
        average_row = [round(val / num_dates) for val in average_row]
    
    # Add average row at the END (so it appears at TOP)
    z_data_summary.append(average_row)
    y_labels_summary.append(f"📊 Average (across {num_dates} days)")
    
    average_row_index = len(y_labels_summary) - 1
    
    # **UPDATED: Create text array with black color for average row**
    text_data = []
    for j, row in enumerate(z_data_summary):
        text_data.append([str(val) if val > 0 else '' for val in row])
    
    # Main heatmap - no text (we'll add it via annotations)
    fig_summary = go.Figure(data=go.Heatmap(
        z=z_data_summary,
        x=times,
        y=y_labels_summary,
        colorscale=[
            [0, 'white'],
            [0.5, '#ff6b6b'],
            [1, '#e74c3c']
        ],
        showscale=False,
        text=text_data,
        texttemplate="",  # Don't show text from heatmap
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br>Time: %{x}<br>Reservations: %{z}<extra></extra>"
    ))
    
# Add vertical solid black lines at 1-hour intervals (on left edge of cells)
    for i in range(0, len(times), 6):  # Every 6 slots = 1 hour (60 minutes)
        x_pos = i - 0.5  # Position at left edge of cell
        
        fig_summary.add_shape(
            type="line",
            x0=x_pos,
            x1=x_pos,
            y0=-0.5,
            y1=len(y_labels_summary) - 0.5,
            line=dict(color="black", width=0.2),  # Solid black line
            xref="x",
            yref="y"
        )
    
    # **NEW: Add horizontal lines above and below AVERAGE row**
    # Line below AVERAGE row
    fig_summary.add_shape(
        type="line",
        x0=-0.5,
        x1=len(times) - 0.5,
        y0=average_row_index - 0.5,
        y1=average_row_index - 0.5,
        line=dict(color="black", width=1),
        xref="x",
        yref="y"
    )
    
    # Line above AVERAGE row
    fig_summary.add_shape(
        type="line",
        x0=-0.5,
        x1=len(times) - 0.5,
        y0=average_row_index + 0.5,
        y1=average_row_index + 0.5,
        line=dict(color="black", width=1),
        xref="x",
        yref="y"
    )
    
    # **NEW: Add separator lines above each Monday (except first occurrence)**
    # This helps distinguish different weeks
    prev_day = None
    for j, label in enumerate(y_labels_summary):
        # Extract day of week from label (e.g., "📅 9/28 (Mo)" -> "Mo")
        if "(" in label and ")" in label:
            day_part = label.split("(")[1].split(")")[0]
            
            # If this is Monday and not the first row
            if day_part == "Mo" and prev_day is not None:
                # Draw separator line above this Monday
                fig_summary.add_shape(
                    type="line",
                    x0=-0.5,
                    x1=len(times) - 0.5,
                    y0=j + 0.5,
                    y1=j + 0.5,
                    line=dict(color="black", width=0.8),
                    xref="x",
                    yref="y"
                )
            
            prev_day = day_part
    
    # **NEW: Add black borders around cells that exceed cap**
    # Group consecutive cells that exceed cap
    for j, label in enumerate(y_labels_summary):
        i = 0
        while i < len(times):
            val = z_data_summary[j][i]
            if val >= location_cap:
                # Found a cell that exceeds cap, find consecutive cells
                start_i = i
                while i < len(times) and z_data_summary[j][i] >= location_cap:
                    i += 1
                end_i = i
                
                # Draw border around this group of cells
                fig_summary.add_shape(
                    type="rect",
                    x0=start_i - 0.5,
                    x1=end_i - 0.5,
                    y0=j - 0.5,
                    y1=j + 0.5,
                    line=dict(color="black", width=1.5),
                    fillcolor="rgba(0,0,0,0)",  # Transparent fill
                    xref="x",
                    yref="y"
                )
            else:
                i += 1
    
    # **NEW: Add outer border around entire heatmap**
    fig_summary.add_shape(
        type="rect",
        x0=-0.5,
        x1=len(times) - 0.5,
        y0=-0.5,
        y1=len(y_labels_summary) - 0.5,
        line=dict(color="black", width=0.5),
        fillcolor="rgba(0,0,0,0)",  # Transparent fill
        xref="x",
        yref="y"
    )
    
    # **FIXED: Combine all annotations together**
    all_annotations = []
    
    # Add text annotations for ALL cells with correct colors
    for j, label in enumerate(y_labels_summary):
        for i, time in enumerate(times):
            val = z_data_summary[j][i]
            if val > 0:
                all_annotations.append(
                    dict(
                        x=time,
                        y=label,
                        text=str(int(val)),
                        showarrow=False,
                        font=dict(
                            size=12,
                            color="black" if j == average_row_index else "white"
                        ),
                        xref="x",
                        yref="y"
                    )
                )
    
    # Add top x-axis labels
    for i, time in enumerate(times):
        if i % 3 == 0:  # Show every 3rd label (30-minute intervals)
            all_annotations.append(
                dict(
                    x=time,
                    y=1.02,
                    xref='x',
                    yref='paper',
                    text=time,
                    showarrow=False,
                    textangle=45,
                    xanchor='center',
                    yanchor='bottom',
                    font=dict(size=12.5)
                )
            )
    
    title = f""
    if selected_location_date and selected_location_date != "All Dates":
        title += f" - {selected_location_date}"
    
    # **FIXED: Single update_layout call with all annotations**
    fig_summary.update_layout(
        title=title,
        yaxis_title="Date",
        height=max(400, (len(sorted_location_dates) + 1) * 50 + 150),  # +1 for average row
        xaxis=dict(
            tickangle=45,
            tickmode='linear',
            dtick=3,
            side='bottom',
            title="Time"
        ),
        yaxis=dict(
            tickfont=dict(size=11)
        ),
        margin=dict(l=120, r=50, t=70, b=100),
        showlegend=False,
        annotations=all_annotations  # All annotations in one go!
    )
    
    # Return sorted location-date groups to maintain order (reversed for display)
    sorted_location_date_groups = {ld: location_date_groups[ld] for ld in reversed(sorted_location_dates)}
    
    return fig_summary, sorted_location_date_groups

# Main application
def main():
    st.title("📅 Time Reservation Management System")
    st.markdown("**Visualizes reservation status with ±30 minute buffer time applied**")
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Settings")
    
    # Data input method selection
    data_input_method = st.sidebar.radio(
        "Data Input Method",
        ["Use Sample Data", "Upload CSV File"]
    )
    
    data = DEFAULT_DATA.copy()
    
    if data_input_method == "Upload CSV File":
        uploaded_file = st.sidebar.file_uploader("Select CSV file", type="csv")
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                required_columns = ['location', 'id', 'datetime']
                if all(col in df.columns for col in required_columns):
                    data = df.to_dict('records')
                    st.sidebar.success(f"✅ Loaded {len(data)} reservation records.")
                else:
                    st.sidebar.error(f"❌ CSV file must contain columns: {', '.join(required_columns)}")
            except Exception as e:
                st.sidebar.error(f"❌ File reading error: {e}")
     
# Process data: extract time and create location_date field (date only, no location name)
    for item in data:
        item['time'] = extract_time_only(item['datetime'])
        item['date'] = extract_date_only(item['datetime'])
        item['day_of_week'] = get_day_of_week(item['datetime'])
        item['location_date'] = item['date']  # Only date, no location name
    
    # Extract unique locations from data
    all_locations = sorted(list(set([item['location'] for item in data])))
    default_location = "Denver" if "Denver" in all_locations else all_locations[0]
    
    # Location selector
    selected_location = st.selectbox(
        "📍 Select Location",
        all_locations,
        index=all_locations.index(default_location),
        label_visibility="visible"
    )
    
    # Filter data by selected location
    location_filtered_data = [item for item in data if item['location'] == selected_location]
    
    st.sidebar.markdown(f"**Total records in {selected_location}:** {len(location_filtered_data)}")
    
    # Operating hours configuration
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏰ Operating Hours")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_hour = st.selectbox("Start Hour", range(0, 24), index=6)
    with col2:
        end_hour = st.selectbox("End Hour", range(1, 25), index=21)
    
    if start_hour >= end_hour:
        st.sidebar.error("⚠️ End hour must be later than start hour.")
        return
    
    # Location-Date filter (only for selected location)
    location_dates = sorted(list(set([item['location_date'] for item in location_filtered_data])),
                           key=lambda ld: extract_full_date([item for item in location_filtered_data if item['location_date'] == ld][0]['datetime']))
    
    st.sidebar.markdown("---")
    selected_location_date = st.sidebar.selectbox(
        "📅 Filter by Date",
        ["All Dates"] + location_dates
    )
    
    # Data processing
    time_slots, reservation_data = calculate_time_slots(location_filtered_data, start_hour, end_hour, 
                                                         None if selected_location_date == "All Dates" else selected_location_date)
    
    # Show filtering info
    total_filtered = len(reservation_data)
    total_original = len([item for item in location_filtered_data if selected_location_date == "All Dates" or item['location_date'] == selected_location_date])
    
    if total_filtered < total_original:
        filtered_out = total_original - total_filtered
        st.info(f"ℹ️ {filtered_out} reservations are hidden (outside time range considering ±30min buffer)")
    
# Weekly Average Heatmap
    st.subheader("📊 Weekly Average Pattern")
    
    # Calculate day-of-week averages
    day_order = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    day_counts = {day: {} for day in day_order}  # {day: {time_index: [values]}}
    
    # Group data by day of week
    for item in reservation_data:
        day = item.get('day_of_week', '')
        if day not in day_order:
            continue
            
        original_minutes = time_to_minutes(item['time'])
        start_minutes = original_minutes - 30
        end_minutes = original_minutes + 30
        
        for i, slot in enumerate(time_slots):
            slot_minutes = slot['minutes']
            if start_minutes <= slot_minutes < end_minutes:
                if i not in day_counts[day]:
                    day_counts[day][i] = []
                day_counts[day][i].append(1)
    
# Calculate averages for each day-time combination
    times = [slot['time'] for slot in time_slots]
    z_data_weekly = []
    y_labels_weekly = []
    
    for day in reversed(day_order):  # Reverse to show Mo at top
        row = []
        for i in range(len(time_slots)):
            if i in day_counts[day] and day_counts[day][i]:
                # Calculate average with decimal (keep precision internally)
                num_dates_for_day = len(set([item['date'] for item in reservation_data if item.get('day_of_week') == day]))
                avg = sum(day_counts[day][i]) / num_dates_for_day if num_dates_for_day > 0 else 0
                row.append(avg)  # Keep decimal for internal calculation
            else:
                row.append(0)
        z_data_weekly.append(row)
        y_labels_weekly.append(day)
    
    # Create text data for display (integers only)
    text_data_weekly = [[str(int(round(val))) if val > 0 else '' for val in row] for row in z_data_weekly]
    
    # Get location cap
    location_cap = get_location_cap(selected_location)
    
    # Create weekly heatmap
    fig_weekly = go.Figure(data=go.Heatmap(
        z=z_data_weekly,
        x=times,
        y=y_labels_weekly,
        colorscale=[
            [0, 'white'],
            [0.5, '#ff6b6b'],
            [1, '#e74c3c']
        ],
        showscale=False,
        text=text_data_weekly,
        texttemplate="",
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br>Time: %{x}<br>Average: %{z:.1f}<extra></extra>"
    ))
    
    # Add vertical lines at 1-hour intervals
    for i in range(0, len(times), 6):
        x_pos = i - 0.5
        fig_weekly.add_shape(
            type="line",
            x0=x_pos, x1=x_pos,
            y0=-0.5, y1=len(y_labels_weekly) - 0.5,
            line=dict(color="black", width=0.2),
            xref="x", yref="y"
        )
    
# Add black borders for cells exceeding cap
    # For weekly average, use cap - 1 as threshold
    weekly_cap_threshold = max(1, location_cap - 1)
    
    for j, day in enumerate(y_labels_weekly):
        i = 0
        while i < len(times):
            val = z_data_weekly[j][i]
            if val >= weekly_cap_threshold:
                start_i = i
                while i < len(times) and z_data_weekly[j][i] >= weekly_cap_threshold:
                    i += 1
                end_i = i
                
                fig_weekly.add_shape(
                    type="rect",
                    x0=start_i - 0.5, x1=end_i - 0.5,
                    y0=j - 0.5, y1=j + 0.5,
                    line=dict(color="black", width=3),
                    fillcolor="rgba(0,0,0,0)",
                    xref="x", yref="y"
                )
            else:
                i += 1
    
    # Add text annotations
    annotations_weekly = []
    for j, day in enumerate(y_labels_weekly):
        for i, time in enumerate(times):
            val = z_data_weekly[j][i]
            if val > 0:
                annotations_weekly.append(dict(
                    x=time, y=day,
                    text=str(int(round(val))),  # Display as integer
                    showarrow=False,
                    font=dict(size=12, color="white"),
                    xref="x", yref="y"
                ))
    
    # Add top x-axis labels
    for i, time in enumerate(times):
        if i % 3 == 0:
            annotations_weekly.append(dict(
                x=time, y=1.02,
                xref='x', yref='paper',
                text=time,
                showarrow=False,
                textangle=45,
                xanchor='center',
                yanchor='bottom',
                font=dict(size=12.5)
            ))
    
    fig_weekly.update_layout(
        title="",
        xaxis_title="Time",
        yaxis_title="Day of Week",
        height=400,
        xaxis=dict(tickangle=45, tickmode='linear', dtick=3, side='bottom'),
        yaxis=dict(tickfont=dict(size=11)),
        margin=dict(l=80, r=50, t=70, b=100),
        showlegend=False,
        annotations=annotations_weekly
    )
    
    st.plotly_chart(fig_weekly, use_container_width=True)

    # Main content - Reservation Chart
    st.subheader(f"📊 Reservation Status: {selected_location}")
    
    # Legend
    st.markdown("""
    <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 20px;">
        <div class="legend-item">
            <div class="legend-color" style="background-color: white; border: 2px solid #ccc;"></div>
            <span>Available</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #ff6b6b;"></div>
            <span>Reserved</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #e74c3c;"></div>
            <span>Overlapping</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Summary heatmap and location-date details
    if reservation_data:
        fig_summary, location_date_groups = create_heatmap(time_slots, reservation_data, 
                                                           None if selected_location_date == "All Dates" else selected_location_date,
                                                           selected_location)
        
        # Display location cap info
        location_cap = get_location_cap(selected_location)
        st.info(f"📊 **{selected_location} Capacity Cap: {location_cap}** - Times exceeding cap are marked with black borders")
        
        st.plotly_chart(fig_summary, use_container_width=True)
        
    else:
        st.info(f"ℹ️ No reservations to display for {selected_location}.")

if __name__ == "__main__":
    main()