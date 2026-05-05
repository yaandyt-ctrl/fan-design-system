import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime

from geometry import AxialFanBlade
from bemt import BEMTSolver
from optimizer import optimize_blade
from utils import generate_stl, generate_report
from noise import FanNoisePredictor
from config import DEFAULT_CONFIG

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")
st.success("✅ BEMT + 最佳化版本（已取消 3D 預覽）")

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
        st.success(f"最佳化完成！η = {best_eta:.4f}（提升 {(best_eta/perf['efficiency']-1)*100:.1f}%）")
        blade = opt_blade

# ====================== 徑向分布 ======================
st.subheader("📈 徑向分布")
data = pd.DataFrame({
    "半徑 (m)": blade.r,
    "弦長 (m)": blade.get_chord(),
    "安裝角 (°)": blade.get_beta()
})
st.line_chart(data.set_index("半徑 (m)"))

# ====================== STL 下載 ======================
if st.button("📥 下載 3D STL 模型"):
    generate_stl(blade)
    with open("outputs/optimized_blade.stl", "rb") as f:
        st.download_button("下載 optimized_blade.stl", f.read(), "optimized_blade.stl", "model/stl")

st.caption("✅ 已取消 3D 預覽 | 程式更穩定")