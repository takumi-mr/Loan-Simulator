import streamlit as st
import pandas as pd

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
    current_v_rate = v_init_rate # 現在の適用金利を保持
    discount_factor = 1.0
    
    for m in range(1, years * 12 + 1):
        y = (m - 1) // 12 + 1
        
        # ★修正箇所：その年にスケジュールがあれば適用金利を更新し、以降も保持する
        if y in sch_dict:
            current_v_rate = sch_dict[y]
            
        r = current_v_rate / 1200
        discount_factor *= (1 + r) # 毎月の複利で現在価値に割り引く
        v_limit += target_pmt / discount_factor
        
    st.subheader("結果比較")
    c1, c2 = st.columns(2)
    c1.metric("固定金利での借入限界", f"{int(f_limit/10000):,} 万円")
    c2.metric("変動金利での借入限界", f"{int(v_limit/10000):,} 万円")

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
    current_v_rate = v_init_rate # 現在の適用金利を保持
    
    for y in range(1, years_f + 1):
        # ★修正箇所：その年にスケジュールがあれば適用金利を更新し、以降も保持する
        if y in sch_dict:
            current_v_rate = sch_dict[y]
            
        # 残りの期間と現在の残債、新しい金利で月々の支払額を再計算
        m_pmt = calculate_pmt(curr_bal, current_v_rate, (years_f - y + 1) * 12)
        
        for _ in range(12):
            v_pmts.append(m_pmt)
            interest = curr_bal * (current_v_rate / 1200)
            curr_bal -= (m_pmt - interest)
            
    st.line_chart(pd.DataFrame({
        f"固定金利 ({f_rate_f}%)": [f_pmt] * len(v_pmts),
        "変動金利 (スケジュール適用)": v_pmts
    }))