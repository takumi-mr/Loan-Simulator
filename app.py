import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def calculate_pmt(principal, annual_rate, total_months):
    if annual_rate <= 0: return principal / total_months
    r = annual_rate / 100 / 12
    return principal * r * (1 + r)**total_months / ((1 + r)**total_months - 1)

# --- UI設定 ---
st.set_page_config(page_title="Advanced Loan Sim", layout="wide")
st.title("🏡 ローン比較シミュレーター")

tab1, tab2 = st.tabs(["💰 支払額から逆算 (借入可能額)", "📈 金額から計算 (返済推移)"])

# 共通の変動金利スケジュール設定
with st.sidebar:
    st.header("共通：変動金利設定")
    v_init_rate = st.number_input("初期変動金利 (%)", value=0.5, step=0.1)
    st.write("上昇スケジュール設定")
    # 初期値として6年目、11年目をセット
    df_sch = pd.DataFrame([{"年目": 6, "新金利": 1.0}, {"年目": 11, "新金利": 1.5}])
    edited_sch = st.data_editor(df_sch, num_rows="dynamic")
    
    # 辞書形式に変換 {年: 金利} (空行などは除外)
    edited_sch = edited_sch.dropna()
    sch_dict = dict(zip(edited_sch["年目"], edited_sch["新金利"]))

# --- Tab 1: 逆算ロジック ---
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        target_pmt = st.number_input("毎月の希望支払額 (万円)", value=14.0) * 10000
        years = st.slider("返済期間 (年)", 10, 50, 35, key="t1_y")
        f_rate = st.number_input("固定金利 (%)", value=1.5, step=0.1, key="t1_f")
    
    # 計算 (固定)
    f_limit = target_pmt * ((1 - (1 + f_rate/1200)**-(years*12)) / (f_rate/1200)) if f_rate > 0 else target_pmt * years * 12
    
    # 計算 (変動 - 現在価値の算出)
    v_limit = 0
    current_v_rate = v_init_rate
    discount_factor = 1.0
    
    for m in range(1, years * 12 + 1):
        y = (m - 1) // 12 + 1
        if y in sch_dict:
            current_v_rate = sch_dict[y]
            
        r = current_v_rate / 1200
        discount_factor *= (1 + r)
        v_limit += target_pmt / discount_factor
        
    st.subheader("結果比較")
    c1, c2 = st.columns(2)
    c1.metric("固定金利での借入限界", f"{int(f_limit/10000):,} 万円")
    c2.metric("変動金利での借入限界", f"{int(v_limit/10000):,} 万円")

    st.divider()

    # --- Tab 1: グラフ描画（内訳と累積） ---
    st.subheader("毎月の支払内訳と累積支払額の推移")
    chart_plan = st.radio("グラフに表示するプランを選択", ["固定金利プラン", "変動金利プラン"], horizontal=True)

    # グラフ用データの生成
    months_list = list(range(1, years * 12 + 1))
    principal_portions = []
    interest_portions = []
    cumulative_payments = []
    
    curr_bal = f_limit if chart_plan == "固定金利プラン" else v_limit
    cum_pmt = 0
    current_rate = f_rate if chart_plan == "固定金利プラン" else v_init_rate

    for m in months_list:
        y = (m - 1) // 12 + 1
        
        if chart_plan == "変動金利プラン" and y in sch_dict:
            current_rate = sch_dict[y]
            
        monthly_r = current_rate / 1200
        interest = curr_bal * monthly_r
        
        # 最終月などの微細な誤差を吸収
        principal_paid = target_pmt - interest
        if curr_bal < principal_paid:
            principal_paid = curr_bal
            
        curr_bal -= principal_paid
        cum_pmt += target_pmt
        
        interest_portions.append(interest)
        principal_portions.append(principal_paid)
        cumulative_payments.append(cum_pmt)

    # Plotlyを用いた2軸複合グラフの作成
    fig = go.Figure()

    # 積み上げ棒グラフ: 元本と利息 (左のY軸)
    fig.add_trace(go.Bar(x=months_list, y=principal_portions, name='元本返済分', marker_color='#3498db'))
    fig.add_trace(go.Bar(x=months_list, y=interest_portions, name='利息支払分', marker_color='#e74c3c'))

    # 折れ線グラフ: 累積支払額 (右のY軸)
    fig.add_trace(go.Scatter(
        x=months_list, y=cumulative_payments, name='累積支払額', 
        mode='lines', yaxis='y2', line=dict(color='#2ecc71', width=3)
    ))

    # レイアウトの調整
    fig.update_layout(
        barmode='stack',
        xaxis=dict(title='経過月数'),
        yaxis=dict(title='月々の支払額 (円)', side='left', showgrid=False),
        yaxis2=dict(title='累積支払額 (円)', overlaying='y', side='right', showgrid=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: 正算ロジック (推移) ---
with tab2:
    col1, col2 = st.columns([1, 2])
    with col1:
        principal = st.number_input("借入金額 (万円)", value=4000) * 10000
        years_f = st.slider("返済期間 (年)", 10, 50, 35, key="t2_y")
        f_rate_f = st.number_input("固定金利 (%)", value=1.5, step=0.1, key="t2_f")

    # シミュレーション実行 (固定)
    f_pmt = calculate_pmt(principal, f_rate_f, years_f * 12)
    
    # シミュレーション実行 (変動)
    v_pmts = []
    curr_bal = principal
    current_v_rate = v_init_rate
    
    for y in range(1, years_f + 1):
        if y in sch_dict:
            current_v_rate = sch_dict[y]
            
        m_pmt = calculate_pmt(curr_bal, current_v_rate, (years_f - y + 1) * 12)
        
        for _ in range(12):
            v_pmts.append(m_pmt)
            interest = curr_bal * (current_v_rate / 1200)
            curr_bal -= (m_pmt - interest)
            
    st.line_chart(pd.DataFrame({
        f"固定金利 ({f_rate_f}%)": [f_pmt] * len(v_pmts),
        "変動金利 (スケジュール適用)": v_pmts
    }))