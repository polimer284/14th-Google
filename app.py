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
div[data-baseweb="select"] > div {
    border: 2px solid #2c3e50 !important;
    border-radius: 5px;
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

def get_week_start(date_obj):
    """Get the Monday of the week for a given date"""
    days_since_monday = date_obj.weekday()
    monday = date_obj - timedelta(days=days_since_monday)
    return monday

def get_week_label(monday_date):
    """Generate week label: 'Week 1: 12/1 - 12/7'"""
    sunday = monday_date + timedelta(days=6)
    return f"{monday_date.month}/{monday_date.day} - {sunday.month}/{sunday.day}"

def get_all_weeks(data):
    """Extract all unique weeks from data"""
    weeks = {}
    
    for item in data:
        dt = parse_datetime(item['datetime'])
        if dt:
            monday = get_week_start(dt)
            week_key = monday.strftime("%Y-%m-%d")
            
            if week_key not in weeks:
                weeks[week_key] = {
                    'monday': monday,
                    'label': get_week_label(monday),
                    'dates': set()
                }
            
            weeks[week_key]['dates'].add(item['date'])
    
    # Sort by week start date
    sorted_weeks = sorted(weeks.items(), key=lambda x: x[1]['monday'])
    
    return sorted_weeks

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
    st.title("Concierge Time Table")
    st.markdown("**Visualizes actions with ±30 minute buffer time applied**")
    
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
    # 수정된 코드: 데이터 개수가 많은 순서대로 정렬
    location_counts = {}
    for item in data:
        location = item['location']
        location_counts[location] = location_counts.get(location, 0) + 1

    all_locations = sorted(location_counts.keys(), key=lambda x: location_counts[x], reverse=True)

    default_location = "Denver" if "Denver" in all_locations else all_locations[0]
    
    # Location and Time Frame selectors
    col1, col2, col3 = st.columns([3, 8, 3])

    with col1:
        st.markdown("**📍 Select Location**")
        selected_location = st.selectbox(
            "Select Location",
            all_locations,
            index=all_locations.index(default_location),
            label_visibility="collapsed"
        )

    # Filter data by selected location
    location_filtered_data = [item for item in data if item['location'] == selected_location]

    # Get all weeks from the location-filtered data
    all_weeks = get_all_weeks(location_filtered_data)

    with col2:
        st.markdown("**📅 Select Time Frame**")
        
        # Create options: individual weeks only (no "All Weeks" for multiselect)
        week_options = []
        week_mapping = {}
        
        for i, (week_key, week_info) in enumerate(all_weeks, 1):
            week_label = f"Week {i}: {week_info['label']}"
            week_options.append(week_label)
            week_mapping[week_label] = week_info['dates']
        
        selected_weeks = st.multiselect(
            "Select Time Frame",
            week_options,
            default=week_options,  # 기본값: 모든 주 선택
            label_visibility="collapsed"
        )

    # Filter data by selected weeks
    if not selected_weeks:  # 아무것도 선택 안 했을 때
        week_filtered_data = []
        selected_week_display = "None"
    elif len(selected_weeks) == len(week_options):  # 모든 주 선택
        week_filtered_data = location_filtered_data
        selected_week_display = "All Weeks"
    else:  # 일부 주 선택
        selected_dates = set()
        for week in selected_weeks:
            selected_dates.update(week_mapping[week])
        week_filtered_data = [item for item in location_filtered_data if item['date'] in selected_dates]
        selected_week_display = f"{len(selected_weeks)} week(s) selected"
    
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
    
    # Data processing
    time_slots, reservation_data = calculate_time_slots(week_filtered_data, start_hour, end_hour, None)
    
    # Show combined location and filtering info
    location_cap = get_location_cap(selected_location)
    total_filtered = len(reservation_data)
    total_original = len(week_filtered_data)

    info_parts = [
        f"**{selected_location} Capacity Cap: {location_cap}** - Times exceeding cap are marked with black borders",
        f"**Total records:** {len(week_filtered_data)} (Time Frame: {selected_week_display})"
    ]

    if total_filtered < total_original:
        filtered_out = total_original - total_filtered
        info_parts.append(f"**{filtered_out} reservations are hidden** (outside time range considering ±30min buffer)")

    st.info("\n\n".join(info_parts))
    
    # Weekly Average Heatmap
    st.subheader("Weekly Average Pattern")

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

    # times_with_util 부분 수정
    times_with_util = times + ["", "", "Util. Rate"]  # ← 빈 컬럼 2개 추가

    z_data_weekly = []
    y_labels_weekly = []

    location_cap = get_location_cap(selected_location)

    # Mo, Tu, We, Th, Fr, Sa, Su 순서로 고정
    for day in day_order:  # ← reversed 제거!
        row = []
        total_util = 0
        count_slots = len(time_slots)
        
        for i in range(len(time_slots)):
            if i in day_counts[day] and day_counts[day][i]:
                num_dates_for_day = len(set([item['date'] for item in reservation_data if item.get('day_of_week') == day]))
                avg = sum(day_counts[day][i]) / num_dates_for_day if num_dates_for_day > 0 else 0
                row.append(avg)
                
                util = (avg / location_cap * 100) if location_cap > 0 else 0
                total_util += util
            else:
                row.append(0)
                total_util += 0
        
        avg_util = total_util / count_slots if count_slots > 0 else 0
        row.append(0)
        row.append(0)
        row.append(avg_util)
        
        z_data_weekly.append(row)
        y_labels_weekly.append(day)

    # 각 시간대별 평균 Utilization Row 추가
    time_util_row = []
    for i in range(len(time_slots)):
        # 각 시간 슬롯에 대해 모든 요일의 평균 예약 수 계산
        slot_total = sum([z_data_weekly[j][i] for j in range(len(z_data_weekly))])
        slot_avg = slot_total / len(day_order) if len(day_order) > 0 else 0
        
        # 평균 예약 수를 utilization %로 변환
        util = (slot_avg / location_cap * 100) if location_cap > 0 else 0
        time_util_row.append(util)

    # 빈 컬럼 2개 추가
    time_util_row.append(0)
    time_util_row.append(0)

    # 전체 평균 utilization (오른쪽 아래 코너)
    overall_util = sum(time_util_row[:-2]) / len(time_util_row[:-2]) if len(time_util_row[:-2]) > 0 else 0
    time_util_row.append(overall_util)

    # Overall Avg row 추가
    z_data_weekly.append(time_util_row)
    y_labels_weekly.append("Util. Rate")

    # z_data_weekly_display 수정 - Overall Avg row는 모두 0 (흰색 배경)
    z_data_weekly_display = []
    for row_idx, row in enumerate(z_data_weekly):
        if row_idx == len(z_data_weekly) - 1:  # Overall Avg row
            new_row = [0] * len(row)  # 전체를 0으로 (흰색 배경)
        else:
            new_row = row[:-3] + [0, 0, 0]
        z_data_weekly_display.append(new_row)

    # text_data_weekly 수정 - Overall Avg row는 utilization %로 표시
    text_data_weekly = []
    for row_idx, row in enumerate(z_data_weekly):
        text_row = []
        for col_idx, val in enumerate(row):
            if row_idx == len(z_data_weekly) - 1:  # Overall Avg row
                if col_idx == len(row) - 1:  # 오른쪽 아래 코너 (전체 평균)
                    text_row.append(f"{int(round(val))}%" if val > 0 else '')
                elif col_idx >= len(row) - 3:  # 빈 컬럼들
                    text_row.append('')
                else:  # 각 시간대 utilization - 30분 평균으로 표시
                    if col_idx % 3 == 1:  # 30분의 중간 지점에만 표시 (08:10, 08:40 등)
                        # 이전, 현재, 다음 값의 평균 계산
                        avg_vals = []
                        for offset in [-1, 0, 1]:
                            idx = col_idx + offset
                            if 0 <= idx < len(row) - 3:
                                avg_vals.append(row[idx])
                        avg_30min = sum(avg_vals) / len(avg_vals) if avg_vals else 0
                        text_row.append(f"{int(round(avg_30min))}%" if avg_30min > 0 else '')
                    else:
                        text_row.append('')  # 다른 위치는 빈칸
            else:  # 일반 요일 rows
                if col_idx == len(row) - 1:  # Util Rate 컬럼
                    text_row.append(f"{int(round(val))}%" if val > 0 else '')
                elif col_idx >= len(row) - 3:  # 빈 컬럼들
                    text_row.append('')
                else:  # 일반 시간 슬롯
                    text_row.append(str(int(round(val))) if val > 0 else '')
        text_data_weekly.append(text_row)

    # annotations 수정
    annotations_weekly = []
    for j, day in enumerate(y_labels_weekly):
        for i in range(len(times_with_util)):
            
            # Overall Avg row 처리
            if j == len(y_labels_weekly) - 1:  # Overall Avg row
                if i == len(times_with_util) - 1:  # Util Rate 컬럼 (오른쪽 아래 코너)
                    val = z_data_weekly[j][i]
                    if val > 0:
                        text = f"{int(round(val))}%"
                        color = "black"
                        annotations_weekly.append(dict(
                            x=times_with_util[i], 
                            y=day,
                            text=text,
                            showarrow=False,
                            font=dict(size=12, color=color),
                            xref="x", 
                            yref="y",
                            xanchor='center',
                            yanchor='middle'
                        ))
                elif i < len(times) and i % 3 == 1:  # 30분의 중간 지점에만 표시 (08:10, 08:40 등)
                    # 이전, 현재, 다음 값의 평균 계산
                    avg_vals = []
                    for offset in [-1, 0, 1]:
                        idx = i + offset
                        if 0 <= idx < len(times):
                            avg_vals.append(z_data_weekly[j][idx])
                    avg_30min = sum(avg_vals) / len(avg_vals) if avg_vals else 0
                    
                    if avg_30min > 0:
                        text = f"{int(round(avg_30min))}%"
                        color = "black"
                        annotations_weekly.append(dict(
                            x=times_with_util[i], 
                            y=day,
                            text=text,
                            showarrow=False,
                            font=dict(size=12, color=color),
                            xref="x", 
                            yref="y",
                            xanchor='center',
                            yanchor='middle'
                        ))
            else:  # 일반 요일 rows
                if i == len(times_with_util) - 1:  # Util Rate 컬럼
                    val = z_data_weekly[j][i]
                    if val > 0:
                        text = f"{int(round(val))}%"
                        color = "black"
                        annotations_weekly.append(dict(
                            x=times_with_util[i], 
                            y=day,
                            text=text,
                            showarrow=False,
                            font=dict(size=12, color=color),
                            xref="x", 
                            yref="y",
                            xanchor='center',
                            yanchor='middle'
                        ))
                elif i < len(times):  # 일반 시간 슬롯만
                    val = z_data_weekly[j][i]
                    if val > 0:
                        text = str(int(round(val)))
                        color = "white"
                        annotations_weekly.append(dict(
                            x=times_with_util[i], 
                            y=day,
                            text=text,
                            showarrow=False,
                            font=dict(size=12, color=color),
                            xref="x", 
                            yref="y"
                        ))

    fig_weekly = go.Figure(data=go.Heatmap(
        z=z_data_weekly_display,
        x=times_with_util,
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
        hovertemplate="<b>%{y}</b><br>Time: %{x}<br>Value: %{z:.1f}<extra></extra>",
        xgap=0,  # ← 추가: 수평 그리드 라인 제거
        ygap=0   # ← 추가: 수직 그리드 라인도 제거
    ))

    # Add separator line above Overall Avg row
    fig_weekly.add_shape(
        type="line",
        x0=-0.5, x1=len(times_with_util) - 0.5,
        y0=-0.5, y1=-0.5,  # Overall Avg row 위
        line=dict(color="black", width=0.2),
        xref="x", yref="y"
    )
    # Add vertical lines every 6 time slots (every hour)
    for i in range(0, len(times), 6):
        x_pos = i - 0.5
        fig_weekly.add_shape(
            type="line",
            x0=x_pos, x1=x_pos,
            y0=-0.5, y1=len(y_labels_weekly) - 0.5,
            line=dict(color="black", width=0.2),
            xref="x", yref="y"
        )

    # Add separator line before Utilization Rate column
    fig_weekly.add_shape(
        type="line",
        x0=len(times) - 0.5, x1=len(times) - 0.5,
        y0=-0.5, y1=len(y_labels_weekly) - 0.5,
        line=dict(color="black", width=0.2),
        xref="x", yref="y"
    )

    weekly_cap_threshold = max(1, location_cap - 1)

    for j, day in enumerate(y_labels_weekly):
        # Util. Rate 행은 검은색 박스 로직 제외
        if j == len(y_labels_weekly) - 1:  # 마지막 행 (Util. Rate)
            continue
        
        i = 0
        while i < len(times):  # Only check time slots, not utilization column
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

    # Add time labels at the top
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

    # Add "Util. Rate" label
    annotations_weekly.append(dict(
        x="Util. Rate", y=1.02,
        xref='x', yref='paper',
        text="Util. Rate",
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
        xaxis=dict(
            tickangle=45, 
            tickmode='linear',
            dtick=3,
            side='bottom',
            showgrid=False  # ← 추가
        ),
        yaxis=dict(
            tickfont=dict(size=11),
            showgrid=False,
            autorange='reversed'  # 또는 categoryorder='array', categoryarray=y_labels_weekly
        ),
        margin=dict(l=80, r=20, t=70, b=100),  # ← r=20으로 변경
        showlegend=False,
        annotations=annotations_weekly,
        plot_bgcolor='white'  # ← 추가: 배경색 흰색
    )

    st.plotly_chart(fig_weekly, use_container_width=True)

    # Main content - Reservation Chart
    st.subheader(f"Daily Pattern: {selected_location}")
    
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
                                                        None,
                                                        selected_location)
        st.plotly_chart(fig_summary, use_container_width=True)
        
    else:
        st.info(f"ℹ️ No reservations to display for {selected_location}.")

if __name__ == "__main__":
    main()