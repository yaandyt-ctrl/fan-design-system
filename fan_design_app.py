import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime

# 使用 plotly.express（Cloud 最穩定）
import plotly.express as px

from geometry import AxialFanBlade
from bemt import BEMTSolver
from optimizer import optimize_blade
from utils import generate_stl, generate_report
from noise import FanNoisePredictor
from config import DEFAULT_CONFIG

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")
st.success("✅ 完整 BEMT + 最佳化版本已載入")

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

# ====================== 主計算 ======================
blade = AxialFanBlade(R_tip, hub_ratio, N_blades)
blade.params['chord_ctrl'] = np.array([0.12, 0.18, 0.15, 0.10])  # 預設值，可後續加滑桿
blade.params['beta_ctrl'] = np.array([55, 45, 35, 28])

bemt = BEMTSolver(blade, RPM)
perf = bemt.calculate_performance(Q_design)

col1, col2 = st.columns(2)
with col1:
    st.metric("靜壓效率 η", f"{perf['efficiency']:.4f}")
with col2:
    st.metric("推力 (N)", f"{perf['thrust']:.2f}")

if optimize_flag and st.button("🚀 執行效率最佳化", type="primary"):
    with st.spinner("最佳化計算中..."):
        opt_blade, best_eta = optimize_blade(blade, bemt, Q_design, DeltaP_design)
        st.success(f"最佳化完成！η = {best_eta:.4f}")

# ====================== 徑向分布 ======================
st.subheader("徑向分布")
fig = px.line(x=blade.r, y=blade.get_chord(), labels={'x':'半徑 (m)', 'y':'弦長 (m)'}, title="弦長分布")
st.plotly_chart(fig, use_container_width=True)

fig2 = px.line(x=blade.r, y=blade.get_beta(), labels={'x':'半徑 (m)', 'y':'安裝角 (°)'}, title="安裝角分布")
st.plotly_chart(fig2, use_container_width=True)

# ====================== STL 下載 ======================
if st.button("📥 下載 3D STL 模型"):
    generate_stl(blade)
    with open("outputs/optimized_blade.stl", "rb") as f:
        st.download_button("下載 optimized_blade.stl", f.read(), "optimized_blade.stl", "model/stl")

st.caption("✅ 已成功部署 | BEMT 計算 + 最佳化功能已恢復")