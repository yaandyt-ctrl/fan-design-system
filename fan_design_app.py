import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

# ==================== 您的其他 import ====================
from geometry import AxialFanBlade
from bemt import BEMTSolver
from optimizer import optimize_blade
from utils import generate_stl, generate_report
from noise import FanNoisePredictor
from config import DEFAULT_CONFIG

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")

with st.sidebar:
    st.header("設計條件")
    R_tip = st.slider("葉尖半徑 (m)", 0.05, 0.5, DEFAULT_CONFIG['R_tip'], 0.005)
    hub_ratio = st.slider("輪轂比", 0.6, 0.9, DEFAULT_CONFIG['R_hub_ratio'], 0.01)
    N_blades = st.slider("葉片數", 5, 15, DEFAULT_CONFIG['N_blades'], 1)
    RPM = st.slider("轉速 RPM", 500, 3000, DEFAULT_CONFIG['RPM'], 50)
    Q_design = st.number_input("設計流量 Q (m³/s)", 0.1, 2.0, DEFAULT_CONFIG['Q_design'], 0.01)
    DeltaP_design = st.number_input("設計靜壓 ΔP (Pa)", 50, 500, DEFAULT_CONFIG['DeltaP_design'], 5)

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
    blade.params['chord_ctrl'] = np.array([c0,c1,c2,c3])
    blade.params['beta_ctrl'] = np.array([b0,b1,b2,b3])
    bemt = BEMTSolver(blade, RPM)
    perf = bemt.calculate_performance(Q_design)
    st.metric("效率 η", f"{perf['efficiency']:.4f}")
    st.metric("推力 (N)", f"{perf['thrust']:.2f}")

if st.button("🚀 執行效率最佳化"):
    with st.spinner("最佳化中..."):
        opt_blade, best_eta = optimize_blade(blade, bemt, Q_design, DeltaP_design)
        st.success(f"最佳化完成！η = {best_eta:.4f}")

tab1, tab2, tab3 = st.tabs(["📈 徑向分布", "🌀 3D 葉片", "🔊 噪音"])
# （其餘 tab 可後續擴充）

st.caption("專案已準備好！")
