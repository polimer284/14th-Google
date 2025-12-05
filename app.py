import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import random
import gspread
from google.oauth2.service_account import Credentials

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
    "default": 3
}

def get_location_cap(location):
    """Get capacity cap for a location"""
    return LOCATION_CAPS.get(location, LOCATION_CAPS["default"])

# Google Sheets connection
@st.cache_resource
def get_gsheet_connection():
    """Connect to Google Sheets using service account credentials"""
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Get credentials from Streamlit secrets
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )
        
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Google Sheets 연결 실패: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_from_gsheet():
    """Load data from Google Sheets"""
    try:
        client = get_gsheet_connection()
        if client is None:
            return None
        
        # Get the sheet URL or ID from secrets
        sheet_url = st.secrets.get("gsheet_url", "")
        
        if not sheet_url:
            st.error("❌ Google Sheet URL이 설정되지 않았습니다.")
            return None
        
        # Open the sheet
        sheet = client.open_by_url(sheet_url).sheet1
        
        # Get all records
        records = sheet.get_all_records()
        
        if not records:
            st.warning("⚠️ Google Sheet에 데이터가 없습니다.")
            return None
        
        return records
        
    except Exception as e:
        st.error(f"❌ 데이터 로드 실패: {e}")
        return None

# Sample data for fallback
def generate_sample_data():
    locations = ["Denver", "New York", "Los Angeles", "Chicago", "Boston"]
    sample_times = [
        "5:30 PM", "9:30 AM", "2:48 PM", "5:30 PM", "2:48 PM", "4:25 PM", 
        "9:40 AM", "10:00 AM", "9:44 AM", "3:45 PM", "4:30 PM", "9:49 AM",
        "8:00 AM", "4:50 PM", "10:20 AM", "10:56 AM", "6:33 AM", "12:00 PM"
    ]
    sample_dates = ["9/28/25", "9/29/25", "9/30/25"]
    
    data = []
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
    if selected_location_date and selected_location_date != "All Dates":
        data = [item for item in data if item['location_date'] == selected_location_date]
    
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
    
    start_minutes = start_hour * 60
    end_minutes = end_hour * 60
    
    filtered_data = []
    for item in data:
        reservation_minutes = time_to_minutes(item['time'])
        reservation_start = reservation_minutes - 30
        reservation_end = reservation_minutes + 30
        
        if reservation_end > start_minutes and reservation_start < end_minutes:
            filtered_data.append(item)
    
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

def create_heatmap(time_slots, data, selected_location_date=None, selected_location=None):
    """Create heatmap chart grouped by location-date with expandable details"""
    location_cap = get_location_cap(selected_location) if selected_location else LOCATION_CAPS["default"]
    
    times = [slot['time'] for slot in time_slots]
    
    location_date_groups = {}
    for item in data:
        location_date = item['location_date']
        if location_date not in location_date_groups:
            location_date_groups[location_date] = []
        location_date_groups[location_date].append(item)
    
    sorted_location_dates = sorted(location_date_groups.keys(), 
                                   key=lambda ld: extract_full_date(location_date_groups[ld][0]['datetime']))
    
    z_data_summary = []
    y_labels_summary = []
    
    num_dates = len(sorted_location_dates)
    average_row = [0] * len(time_slots)
    
    for location_date in reversed(sorted_location_dates):
        location_date_items = location_date_groups[location_date]
        day_of_week = location_date_items[0].get('day_of_week', '')
        
        location_date_total_row = [0] * len(time_slots)
        for item in location_date_items:
            original_minutes = time_to_minutes(item['time'])
            start_minutes = original_minutes - 30
            end_minutes = original_minutes + 30
            
            for i, slot in enumerate(time_slots):
                slot_minutes = slot['minutes']
                if start_minutes <= slot_minutes < end_minutes:
                    location_date_total_row[i] += 1
        
        for i in range(len(time_slots)):
            average_row[i] += location_date_total_row[i]
        
        z_data_summary.append(location_date_total_row)
        y_labels_summary.append(f"📅 {location_date} ({day_of_week})")
    
    if num_dates > 0:
        average_row = [round(val / num_dates) for val in average_row]
    
    z_data_summary.append(average_row)
    y_labels_summary.append(f"📊 Average (across {num_dates} days)")
    
    average_row_index = len(y_labels_summary) - 1
    
    text_data = []
    for j, row in enumerate(z_data_summary):
        text_data.append([str(val) if val > 0 else '' for val in row])
    
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
        texttemplate="",
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br>Time: %{x}<br>Reservations: %{z}<extra></extra>"
    ))
    
    for i in range(0, len(times), 6):
        x_pos = i - 0.5
        fig_summary.add_shape(
            type="line",
            x0=x_pos, x1=x_pos,
            y0=-0.5, y1=len(y_labels_summary) - 0.5,
            line=dict(color="black", width=0.2),
            xref="x", yref="y"
        )
    
    fig_summary.add_shape(
        type="line",
        x0=-0.5, x1=len(times) - 0.5,
        y0=average_row_index - 0.5, y1=average_row_index - 0.5,
        line=dict(color="black", width=1),
        xref="x", yref="y"
    )
    
    fig_summary.add_shape(
        type="line",
        x0=-0.5, x1=len(times) - 0.5,
        y0=average_row_index + 0.5, y1=average_row_index + 0.5,
        line=dict(color="black", width=1),
        xref="x", yref="y"
    )
    
    prev_day = None
    for j, label in enumerate(y_labels_summary):
        if "(" in label and ")" in label:
            day_part = label.split("(")[1].split(")")[0]
            if day_part == "Mo" and prev_day is not None:
                fig_summary.add_shape(
                    type="line",
                    x0=-0.5, x1=len(times) - 0.5,
                    y0=j + 0.5, y1=j + 0.5,
                    line=dict(color="black", width=0.8),
                    xref="x", yref="y"
                )
            prev_day = day_part
    
    for j, label in enumerate(y_labels_summary):
        i = 0
        while i < len(times):
            val = z_data_summary[j][i]
            if val >= location_cap:
                start_i = i
                while i < len(times) and z_data_summary[j][i] >= location_cap:
                    i += 1
                end_i = i
                
                fig_summary.add_shape(
                    type="rect",
                    x0=start_i - 0.5, x1=end_i - 0.5,
                    y0=j - 0.5, y1=j + 0.5,
                    line=dict(color="black", width=1.5),
                    fillcolor="rgba(0,0,0,0)",
                    xref="x", yref="y"
                )
            else:
                i += 1
    
    fig_summary.add_shape(
        type="rect",
        x0=-0.5, x1=len(times) - 0.5,
        y0=-0.5, y1=len(y_labels_summary) - 0.5,
        line=dict(color="black", width=0.5),
        fillcolor="rgba(0,0,0,0)",
        xref="x", yref="y"
    )
    
    all_annotations = []
    
    for j, label in enumerate(y_labels_summary):
        for i, time in enumerate(times):
            val = z_data_summary[j][i]
            if val > 0:
                all_annotations.append(
                    dict(
                        x=time, y=label,
                        text=str(int(val)),
                        showarrow=False,
                        font=dict(
                            size=12,
                            color="black" if j == average_row_index else "white"
                        ),
                        xref="x", yref="y"
                    )
                )
    
    for i, time in enumerate(times):
        if i % 3 == 0:
            all_annotations.append(
                dict(
                    x=time, y=1.02,
                    xref='x', yref='paper',
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
    
    fig_summary.update_layout(
        title=title,
        yaxis_title="Date",
        height=max(400, (len(sorted_location_dates) + 1) * 50 + 150),
        xaxis=dict(
            tickangle=45,
            tickmode='linear',
            dtick=3,
            side='bottom',
            title="Time"
        ),
        yaxis=dict(tickfont=dict(size=11)),
        margin=dict(l=120, r=50, t=70, b=100),
        showlegend=False,
        annotations=all_annotations
    )
    
    sorted_location_date_groups = {ld: location_date_groups[ld] for ld in reversed(sorted_location_dates)}
    
    return fig_summary, sorted_location_date_groups

def main():
    st.title("📅 Time Reservation Management System")
    st.markdown("**Visualizes reservation status with ±30 minute buffer time applied**")
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Settings")
    
    # Data source selection
    data_source = st.sidebar.radio(
        "Data Source",
        ["Google Sheets", "Sample Data", "Upload CSV"]
    )
    
    data = None
    
    if data_source == "Google Sheets":
        with st.spinner("📊 Loading data from Google Sheets..."):
            data = load_data_from_gsheet()
            if data:
                st.sidebar.success(f"✅ Loaded {len(data)} records from Google Sheets")
                # Add refresh button
                if st.sidebar.button("🔄 Refresh Data"):
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.sidebar.warning("⚠️ Failed to load from Google Sheets. Using sample data.")
                data = DEFAULT_DATA.copy()
    
    elif data_source == "Sample Data":
        data = DEFAULT_DATA.copy()
        st.sidebar.info(f"📊 Using sample data ({len(data)} records)")
    
    else:  # Upload CSV
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
                    data = DEFAULT_DATA.copy()
            except Exception as e:
                st.sidebar.error(f"❌ File reading error: {e}")
                data = DEFAULT_DATA.copy()
        else:
            data = DEFAULT_DATA.copy()
    
    if not data:
        st.error("❌ No data available")
        return
    
    # Process data
    for item in data:
        item['time'] = extract_time_only(item['datetime'])
        item['date'] = extract_date_only(item['datetime'])
        item['day_of_week'] = get_day_of_week(item['datetime'])
        item['location_date'] = item['date']
    
    # Extract unique locations
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
    
    # Location-Date filter
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
    
    day_order = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    day_counts = {day: {} for day in day_order}
    
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
    
    times = [slot['time'] for slot in time_slots]
    z_data_weekly = []
    y_labels_weekly = []
    
    for day in reversed(day_order):
        row = []
        for i in range(len(time_slots)):
            if i in day_counts[day] and day_counts[day][i]:
                num_dates_for_day = len(set([item['date'] for item in reservation_data if item.get('day_of_week') == day]))
                avg = sum(day_counts[day][i]) / num_dates_for_day if num_dates_for_day > 0 else 0
                row.append(avg)
            else:
                row.append(0)
        z_data_weekly.append(row)
        y_labels_weekly.append(day)
    
    text_data_weekly = [[str(int(round(val))) if val > 0 else '' for val in row] for row in z_data_weekly]
    
    location_cap = get_location_cap(selected_location)
    
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
    
    for i in range(0, len(times), 6):
        x_pos = i - 0.5
        fig_weekly.add_shape(
            type="line",
            x0=x_pos, x1=x_pos,
            y0=-0.5, y1=len(y_labels_weekly) - 0.5,
            line=dict(color="black", width=0.2),
            xref="x", yref="y"
        )
    
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
    
    annotations_weekly = []
    for j, day in enumerate(y_labels_weekly):
        for i, time in enumerate(times):
            val = z_data_weekly[j][i]
            if val > 0:
                annotations_weekly.append(dict(
                    x=time, y=day,
                    text=str(int(round(val))),
                    showarrow=False,
                    font=dict(size=12, color="white"),
                    xref="x", yref="y"
                ))
    
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
    
    if reservation_data:
        fig_summary, location_date_groups = create_heatmap(time_slots, reservation_data, 
                                                           None if selected_location_date == "All Dates" else selected_location_date,
                                                           selected_location)
        
        location_cap = get_location_cap(selected_location)
        st.info(f"📊 **{selected_location} Capacity Cap: {location_cap}** - Times exceeding cap are marked with black borders")
        
        st.plotly_chart(fig_summary, use_container_width=True)
        
    else:
        st.info(f"ℹ️ No reservations to display for {selected_location}.")

if __name__ == "__main__":
    main()