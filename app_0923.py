import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# -----------------------------------------------------------------------------
# 1. 페이지 환경 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="제주MBC 시청률 경쟁 비교 대시보드",
    page_icon="📺",
    layout="wide"
)

st.title("제주MBC 타깃 vs 경쟁 프로그램 시청률 정밀 비교 분석")
st.markdown("---")

# 💡 클라우드 및 로컬 환경 동시 대응 (동적 상대 경로)
base_dir = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------------
# 2. 데이터 로드 함수 (다중 경로 자동 탐색)
# -----------------------------------------------------------------------------
@st.cache_data
def load_all_data(base_path, year):
    all_dfs = []
    programs = ["뉴스데스크", "뉴스투데이 제주", "KBS 9시 뉴스", "뉴스광장", "JIBS 8뉴스", "모닝와이드", "뉴스투데이"]
    
    for prog in programs:
        csv_file_name = f"{year}년_{prog}_고급통계분석.csv"
        
        # 1) 메인/현재 폴더 경로 확인
        csv_path = os.path.join(base_path, csv_file_name)
        
        # 2) '프로그램별 시청률/연도' 하위 폴더 확인
        if not os.path.exists(csv_path):
            csv_path = os.path.join(base_path, "프로그램별 시청률", str(year), csv_file_name)
            
        # 3) '프로그램별 시청률' 하위 폴더 확인
        if not os.path.exists(csv_path):
            csv_path = os.path.join(base_path, "프로그램별 시청률", csv_file_name)

        if os.path.exists(csv_path):
            try:
                temp_df = pd.read_csv(csv_path)
                temp_df['Program_Name'] = prog
                all_dfs.append(temp_df)
            except Exception as e:
                st.warning(f"⚠️ {csv_file_name} 로딩 실패: {e}")
            
    if not all_dfs:
        return None
        
    df = pd.concat(all_dfs, ignore_ignore=True) if hasattr(pd.concat(all_dfs), 'ignore_ignore') else pd.concat(all_dfs, ignore_index=True)
    
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        day_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
        df['DayName'] = df['Date'].dt.dayofweek.map(day_map)
        df['Month'] = df['Date'].dt.month
        
    return df

# -----------------------------------------------------------------------------
# 3. 사이드바 비교 필터
# -----------------------------------------------------------------------------
st.sidebar.header("타겟 프로그램 / 경쟁 프로그램 필터")

target_year = st.sidebar.selectbox("연도 선택", [2026, 2025], index=0)
raw_df = load_all_data(base_dir, target_year)

if raw_df is None:
    st.error(f"❌ {target_year}년 시청률 분석 데이터 CSV 파일을 찾을 수 없습니다. GitHub 저장소에 데이터 파일이 존재해야 합니다.")
    st.stop()

available_programs = raw_df['Program_Name'].unique().tolist()

default_target_idx = available_programs.index("뉴스데스크") if "뉴스데스크" in available_programs else 0
focus_program = st.sidebar.selectbox(
    "1. 시청률 비교 기준",
    options=available_programs,
    index=default_target_idx
)

other_programs = [p for p in available_programs if p != focus_program]
selected_competitors = st.sidebar.multiselect(
    "2. 경쟁 프로그램",
    options=other_programs,
    default=other_programs
)

all_selected = [focus_program] + selected_competitors

st.sidebar.markdown("---")
is_single_day = st.sidebar.checkbox("📌 특정일 기준 분석", value=False)

min_date = raw_df['Date'].min().date()
max_date = raw_df['Date'].max().date()

if is_single_day:
    selected_single_date = st.sidebar.date_input(
        "시청률 확인 날짜 선택",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )
    start_date = end_date = selected_single_date
else:
    selected_dates = st.sidebar.date_input(
        "조회 기간 (시작일 ~ 종료일)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif isinstance(selected_dates, tuple) and len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        start_date = end_date = selected_dates

filtered_df = raw_df[
    (raw_df['Program_Name'].isin(all_selected)) &
    (raw_df['Date'].dt.date >= start_date) &
    (raw_df['Date'].dt.date <= end_date)
].copy()

# -----------------------------------------------------------------------------
# 4. 상단 KPI 카드 (단일 출력 처리)
# -----------------------------------------------------------------------------
if is_single_day:
    display_date_str = start_date.strftime('%Y-%m-%d')
    st.subheader(f"[{display_date_str}] 당일 시청률 성과 요약")
else:
    st.subheader("선택 기간 평균 성과 요약")

focus_df = filtered_df[filtered_df['Program_Name'] == focus_program]
focus_rating = focus_df['Rating'].iloc[0] if (is_single_day and not focus_df.empty) else (focus_df['Rating'].mean() if not focus_df.empty else 0)

cols = st.columns(len(all_selected))

for idx, prog in enumerate(all_selected):
    p_df = filtered_df[filtered_df['Program_Name'] == prog]
    with cols[idx]:
        if not p_df.empty:
            curr_rating = p_df['Rating'].iloc[0] if is_single_day else p_df['Rating'].mean()
            metric_title = "당일 시청률" if is_single_day else "평균 시청률"
            
            if prog == focus_program:
                st.markdown(f"### **{prog}** (타깃)")
                st.metric(metric_title, f"{curr_rating:.2f}%")
                if is_single_day:
                    day_name = p_df['DayName'].iloc[0]
                    st.caption(f"방송 요일: {day_name}요일")
                else:
                    st.caption(f"최고: {p_df['Rating'].max():.1f}% | 표준편차: {p_df['Rating'].std():.2f}")
            else:
                diff_vs_target = curr_rating - focus_rating
                st.markdown(f"### {prog}")
                st.metric(metric_title, f"{curr_rating:.2f}%", delta=f"{diff_vs_target:+.2f}%p (타깃 대비)", delta_color="inverse")
                if is_single_day:
                    day_name = p_df['DayName'].iloc[0]
                    st.caption(f"방송 요일: {day_name}요일")
                else:
                    st.caption(f"최고: {p_df['Rating'].max():.1f}% | 표준편차: {p_df['Rating'].std():.2f}")
        else:
            st.markdown(f"### {prog}")
            st.warning("해당 일자 미방송")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. 인터랙티브 비교 차트 탭
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["경쟁사 간 시청률 비교", "월별 시청률 추이", "요일별 비교", "상세 수치"])

# -----------------------------------------------------------------------------
# 📌 탭 1: 타임라인 (월별 첫 실제 방송일 동적 계산 X축 적용)
# -----------------------------------------------------------------------------
with tab1:
    title_suffix = f"({start_date.strftime('%Y-%m-%d')} 당일)" if is_single_day else f"({start_date} ~ {end_date})"
    st.subheader(f"[{focus_program}] vs 경쟁사 일자별 시청률 추이 {title_suffix}")
    
    fig = go.Figure()
    comp_colors = ['#1D3557', '#457B9D', '#2A9D8F', '#E9C46A', '#F4A261', '#9C89B8']
    comp_color_idx = 0

    for prog in all_selected:
        prog_df = filtered_df[filtered_df['Program_Name'] == prog]
        if prog_df.empty:
            continue
            
        x_dates = prog_df['Date'].dt.strftime('%Y-%m-%d')
        
        if prog == focus_program:
            line_color = '#D90429'
            line_width = 3.5
            opacity = 1.0
        else:
            line_color = comp_colors[comp_color_idx % len(comp_colors)]
            comp_color_idx += 1
            line_width = 1.8
            opacity = 0.85

        fig.add_trace(go.Scatter(
            x=x_dates,
            y=prog_df['Rating'],
            mode='lines+markers',
            name=f" {prog}" if prog == focus_program else prog,
            line=dict(color=line_color, width=line_width),
            opacity=opacity,
            marker=dict(size=10 if is_single_day else (5 if prog == focus_program else 3)),
            hovertemplate=f'<b>{prog}</b><br>일자: %{{x}}<br>시청률: %{{y:.2f}}%<extra></extra>'
        ))

    # 💡 [핵심 수정] 각 월(Year-Month)별 '실제 존재하는 첫 방송일'을 추출
    if is_single_day:
        tick_vals = [start_date.strftime('%Y-%m-%d')]
    else:
        # 1. 고유 날짜 데이터셋을 DatetimeIndex 및 DataFrame으로 구성
        unique_dates = pd.DatetimeIndex(filtered_df['Date'].unique()).sort_values()
        date_df = pd.DataFrame({'Date': unique_dates})
        
        # 2. 연-월(Year-Month) 그룹화 후 각 월의 가장 첫 번째(최소) 날짜 추출
        date_df['YearMonth'] = date_df['Date'].dt.to_period('M')
        first_broadcast_days = date_df.groupby('YearMonth')['Date'].min()
        
        # 3. YYYY-MM-DD 문자열 리스트로 변환
        tick_vals = first_broadcast_days.dt.strftime('%Y-%m-%d').tolist()

    fig.update_layout(
        height=550, 
        hovermode="x unified",
        xaxis_title="방송 일자",
        yaxis_title="시청률 (%)",
        xaxis=dict(
            type='category',
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_vals,
            tickangle=0
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 📌 탭 2: 월별 추이 (특정일 모드와 상관없이 연간 데이터 기준 집계)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("월별 시청률 점유 점검 (그룹 막대)")
    
    # 💡 filtered_df 대신 selected 프로그램 전체 연간 raw_df를 사용하여 월평균 계산
    year_selected_df = raw_df[raw_df['Program_Name'].isin(all_selected)]
    monthly_df = year_selected_df.groupby(['Month', 'Program_Name'])['Rating'].mean().reset_index()
    
    fig_m = px.bar(
        monthly_df, 
        x='Month', 
        y='Rating', 
        color='Program_Name', 
        barmode='group',
        text_auto='.2f',
        labels={'Rating': '시청률 (%)', 'Month': '월', 'Program_Name': '프로그램'}
    )
    fig_m.update_layout(height=480, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
    st.plotly_chart(fig_m, use_container_width=True)

# -----------------------------------------------------------------------------
# 📌 탭 3: 요일별 패턴 (특정일 모드와 상관없이 연간 데이터 기준 집계)
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("요일별 평균 시청률 패턴 (월 ~ 일 순서)")
    day_order = ['월', '화', '수', '목', '금', '토', '일']
    
    # 💡 마찬가지로 연간 raw_df 기준으로 요일별 평균 계산
    weekly_df = year_selected_df.groupby(['DayName', 'Program_Name'])['Rating'].mean().reset_index()
    weekly_df['DayName'] = pd.Categorical(weekly_df['DayName'], categories=day_order, ordered=True)
    weekly_df = weekly_df.sort_values(['Program_Name', 'DayName'])

    fig_w = px.line(
        weekly_df, 
        x='DayName', 
        y='Rating', 
        color='Program_Name',
        markers=True,
        text=weekly_df['Rating'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
        labels={'Rating': '평균 시청률 (%)', 'DayName': '요일', 'Program_Name': '프로그램'}
    )
    
    fig_w.update_traces(
        textposition="top center", 
        line=dict(width=2.5), 
        marker=dict(size=7),
        hovertemplate='<b>프로그램=%{fullData.name}</b><br>요일=%{x}<br>평균 시청률 (%)=%{y:.2f}%<extra></extra>'
    )
    
    fig_w.update_layout(
        height=500,
        xaxis=dict(categoryorder='array', categoryarray=day_order),
        yaxis_title="평균 시청률 (%)",
        hovermode="x unified"
    )
    st.plotly_chart(fig_w, use_container_width=True)

# 📌 탭 4: 정밀 통계 표
with tab4:
    st.subheader("시청률 데이터")
    
    display_df = filtered_df.copy()
    display_df['Date_Only'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    
    target_cols = ['Date_Only', 'Program_Name', 'DayName', 'Rating']
    if 'WoW_Diff' in display_df.columns: target_cols.append('WoW_Diff')
    
    st.dataframe(
        display_df[target_cols].rename(
            columns={'Date_Only':'방송일자', 'Program_Name':'프로그램', 'DayName':'요일', 'Rating':'시청률(%)', 'WoW_Diff':'전주대비(%p)'}
        ),
        use_container_width=True
    )
    
    csv_download_df = filtered_df.copy()
    csv_download_df['Date'] = csv_download_df['Date'].dt.strftime('%Y-%m-%d')
    
    st.download_button(
        label="필터링된 데이터(.CSV) 다운로드",
        data=csv_download_df.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"제주MBC_시청률_필터데이터_{target_year}.csv",
        mime='text/csv'
    )
