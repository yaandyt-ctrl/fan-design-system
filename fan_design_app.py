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
st.success("✅ BEMT + 最佳化 + 3D 預覽 已載入")

# ====================== 側邊欄 ======================
with st.sidebar:
    st.header("設計條件")
    R_tip = st.slider("葉尖半徑 R_tip (m)", 0.05, 0.5, 0.25, 0.005)
    hub_ratio = st.slider("輪轂比", 0.1, 0.6, 0.45, 0.01)
    N_blades = st.slider("葉片數", 5, 15, 9, 1)
    RPM = st.slider("轉速 RPM", 500, 3000, 1500, 50)
    Q_design = st.number_input("設計流量 Q (m³/s)", 0.1, 2.0, 0.8, 0.01)
    DeltaP_design = st.number_input("設計靜壓 ΔP (Pa)", 50, 500, 150, 5)
    
    optimize_flag = st.checkbox("執行效率最佳化", value=True)

# ====================== 主計算 ======================
blade = AxialFanBlade(R_tip, hub_ratio, N_blades)
blade.params['chord_ctrl'] = np.array([0.12, 0.18, 0.15, 0.10])
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

# ====================== 3D 葉片預覽 ======================
st.subheader("🌀 3D 葉片預覽（徑向堆疊）")

chords = blade.get_chord()
betas = blade.get_beta()
points = []

for i in range(0, len(blade.r), max(1, len(blade.r)//12)):
    x, y = blade.generate_airfoil_points(chords[i], betas[i])
    z = np.full_like(x, blade.r[i])
    points.append(pd.DataFrame({"x": x*0.4, "y": y*0.4, "z": z, "r": blade.r[i]}))

df_3d = pd.concat(points, ignore_index=True)

fig = px.line_3d(df_3d, x="x", y="y", z="z", color="r", 
                 title="外轉子軸流扇葉 3D 模型",
                 labels={"x": "弦長方向", "y": "厚度方向", "z": "徑向 (m)"})
fig.update_traces(line=dict(width=6))
fig.update_layout(height=650, scene=dict(aspectmode='cube'))

st.plotly_chart(fig, use_container_width=True)

# ====================== STL 下載 ======================
if st.button("📥 下載 3D STL 模型"):
    generate_stl(blade)
    with open("outputs/optimized_blade.stl", "rb") as f:
        st.download_button("下載 optimized_blade.stl", f.read(), "optimized_blade.stl", "model/stl")

st.caption("✅ 3D 預覽 + BEMT + 最佳化 已完整整合")