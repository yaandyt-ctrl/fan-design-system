import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime

# Plotly 正確 import（Cloud 相容版）
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from geometry import AxialFanBlade
from bemt import BEMTSolver
from optimizer import optimize_blade
from utils import generate_stl, generate_report
from noise import FanNoisePredictor
from config import DEFAULT_CONFIG

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")

# ====================== 側邊欄 ======================
with st.sidebar:
    st.header("設計條件")
    R_tip = st.slider("葉尖半徑 R_tip (m)", 0.05, 0.5, DEFAULT_CONFIG['R_tip'], 0.005)
    hub_ratio = st.slider("輪轂比", 0.6, 0.9, DEFAULT_CONFIG['R_hub_ratio'], 0.01)
    N_blades = st.slider("葉片數", 5, 15, DEFAULT_CONFIG['N_blades'], 1)
    RPM = st.slider("轉速 RPM", 500, 3000, DEFAULT_CONFIG['RPM'], 50)
    Q_design = st.number_input("設計流量 Q (m³/s)", 0.1, 2.0, DEFAULT_CONFIG['Q_design'], 0.01)
    DeltaP_design = st.number_input("設計靜壓 ΔP (Pa)", 50, 500, DEFAULT_CONFIG['DeltaP_design'], 5)
    
    optimize_flag = st.checkbox("執行效率最佳化", value=True)

# ====================== 主畫面 ======================
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Bézier 控制點")
    c0 = st.slider("弦長點1", 0.05, 0.30, 0.12, 0.01)
    c1 = st.slider("弦長點2", 0.05, 0.30, 0.18, 0.01)
    c2 = st.slider("弦長點3", 0.05, 0.30, 0.15, 0.01)
    c3 = st.slider("弦長點4", 0.05, 0.30, 0.10, 0.01)
    b0 = st.slider("安裝角點1 (°)", 30, 70, 55, 1)
    b1 = st.slider("安裝角點2 (°)", 30, 70, 45, 1)
    b2 = st.slider("安裝角點3 (°)", 20, 60, 35, 1)
    b3 = st.slider("安裝角點4 (°)", 20, 50, 28, 1)

with col2:
    blade = AxialFanBlade(R_tip, hub_ratio, N_blades)
    blade.params['chord_ctrl'] = np.array([c0, c1, c2, c3])
    blade.params['beta_ctrl'] = np.array([b0, b1, b2, b3])
    
    bemt = BEMTSolver(blade, RPM)
    perf = bemt.calculate_performance(Q_design)
    
    st.metric("靜壓效率 η", f"{perf['efficiency']:.4f}")
    st.metric("推力 (N)", f"{perf['thrust']:.2f}")
    st.metric("功率 (W)", f"{perf['power']:.1f}")

    if optimize_flag and st.button("🚀 執行效率最佳化", type="primary"):
        with st.spinner("最佳化計算中..."):
            opt_blade, best_eta = optimize_blade(blade, bemt, Q_design, DeltaP_design)
            st.success(f"最佳化完成！η = {best_eta:.4f}（提升 {(best_eta/perf['efficiency']-1)*100:.1f}%）")
            blade = opt_blade

# ====================== 分頁 ======================
tab1, tab2, tab3 = st.tabs(["📈 徑向分布", "🌀 3D 葉片預覽", "🔊 噪音預測"])

with tab1:
    fig = make_subplots(rows=1, cols=2, subplot_titles=("弦長分布 (m)", "安裝角分布 (°)"))
    fig.add_trace(go.Scatter(x=blade.r, y=blade.get_chord(), mode='lines+markers'), row=1, col=1)
    fig.add_trace(go.Scatter(x=blade.r, y=blade.get_beta(), mode='lines+markers'), row=1, col=2)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.info("3D 葉片預覽（徑向堆疊）")
    fig3d = go.Figure()
    chords = blade.get_chord()
    betas = blade.get_beta()
    for i in range(0, len(blade.r), max(1, len(blade.r)//8)):
        x, y = blade.generate_airfoil_points(chords[i], betas[i])
        z = np.full_like(x, blade.r[i])
        fig3d.add_trace(go.Scatter3d(x=x*0.4, y=y*0.4, z=z, mode='lines'))
    fig3d.update_layout(height=600, scene=dict(aspectmode='cube'))
    st.plotly_chart(fig3d, use_container_width=True)
    
    if st.button("📥 下載 STL 模型"):
        generate_stl(blade)
        with open("outputs/optimized_blade.stl", "rb") as f:
            st.download_button("下載 optimized_blade.stl", f, "optimized_blade.stl", "model/stl")

with tab3:
    noise = FanNoisePredictor(blade, RPM, Q_design, DeltaP_design)
    spl_total, f_bpf, _, _ = noise.predict_overall_spl()
    st.metric("預估總聲壓級", f"{spl_total:.1f} dBA")

# ====================== 報告 ======================
if st.button("📊 生成設計報告"):
    report = generate_report(blade, perf, {'RPM': RPM, 'Q_design': Q_design, 'DeltaP_design': DeltaP_design})
    st.dataframe(report)

st.caption("✅ 已成功部署到 Streamlit Cloud | 專業工程師版")