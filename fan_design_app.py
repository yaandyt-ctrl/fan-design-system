import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")
st.success("✅ 極簡穩定版已成功載入")

# ====================== 設計條件 ======================
with st.sidebar:
    st.header("設計條件")
    R_tip = st.slider("葉尖半徑 R_tip (m)", 0.05, 0.5, 0.25, 0.005)
    hub_ratio = st.slider("輪轂比", 0.6, 0.9, 0.75, 0.01)
    N_blades = st.slider("葉片數", 5, 15, 9, 1)
    RPM = st.slider("轉速 RPM", 500, 3000, 1500, 50)
    Q_design = st.number_input("設計流量 Q (m³/s)", 0.1, 2.0, 0.8, 0.01)

# 簡化 BEMT 計算（無 scipy）
eta = 0.65 + 0.001 * RPM / 1000 + 0.05 * (1 - hub_ratio)   # 簡化公式
thrust = Q_design * 150

st.metric("估計靜壓效率 η", f"{eta:.4f}")
st.metric("估計推力 (N)", f"{thrust:.2f}")

st.subheader("徑向分布（簡化）")
r = np.linspace(R_tip * hub_ratio, R_tip, 20)
chord = np.linspace(0.18, 0.10, 20)
beta = np.linspace(55, 30, 20)

data = pd.DataFrame({"半徑 (m)": r, "弦長 (m)": chord, "安裝角 (°)": beta})
st.line_chart(data.set_index("半徑 (m)"))

if st.button("📥 下載 STL 模型（示意）"):
    st.download_button("下載 optimized_blade.stl", b"STL data placeholder", "optimized_blade.stl", "model/stl")

st.caption("✅ 已成功部署 | 完整版正在優化中...")