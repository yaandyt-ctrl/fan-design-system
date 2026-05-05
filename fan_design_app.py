import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")
st.success("✅ 已加入 NACA 翼型設計功能")

# ====================== AxialFanBlade（含翼型參數） ======================
class AxialFanBlade:
    def __init__(self, R_tip=0.25, R_hub_ratio=0.45, N_blades=9, num_stations=30):
        self.R_tip = R_tip
        self.R_hub = R_tip * R_hub_ratio
        self.N_blades = N_blades
        self.num_stations = num_stations
        self.r = np.linspace(self.R_hub, self.R_tip, num_stations)
        self.params = {
            'chord_ctrl': np.array([0.12, 0.18, 0.15, 0.10]),
            'beta_ctrl': np.array([55, 45, 35, 28]),
            'm': 0.04,          # 最大彎度
            'p': 0.4,           # 彎度位置
            't': 0.12           # 最大厚度比
        }

    def _bezier_curve(self, t, ctrl_pts):
        n = len(ctrl_pts) - 1
        curve = np.zeros_like(t, dtype=float)
        for i in range(n + 1):
            curve += np.math.comb(n, i) * (1 - t)**(n - i) * t**i * ctrl_pts[i]
        return curve

    def get_chord(self):
        t = np.linspace(0, 1, 4)
        chord_bezier = self._bezier_curve(t, self.params['chord_ctrl'])
        f = lambda x: np.interp(x, np.linspace(0, 1, len(chord_bezier)), chord_bezier)
        return f((self.r - self.R_hub) / (self.R_tip - self.R_hub)) * self.R_tip

    def get_beta(self):
        t = np.linspace(0, 1, 4)
        beta_bezier = self._bezier_curve(t, self.params['beta_ctrl'])
        f = lambda x: np.interp(x, np.linspace(0, 1, len(beta_bezier)), beta_bezier)
        return f((self.r - self.R_hub) / (self.R_tip - self.R_hub))

    def generate_airfoil_points(self, chord, beta):
        """NACA 4-digit 翼型（可調 m, p, t）"""
        m = self.params['m']
        p = self.params['p']
        t = self.params['t']
        x = np.linspace(0, 1, 101)
        yt = 5 * t * (0.2969*x**0.5 - 0.1260*x - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)
        yc = np.where(x < p, m/p**2*(2*p*x - x**2), m/(1-p)**2*((1-2*p) + 2*p*x - x**2))
        dyc_dx = np.where(x < p, 2*m/p**2*(p - x), 2*m/(1-p)**2*(p - x))
        theta = np.arctan(dyc_dx)
        xu = x - yt * np.sin(theta)
        yu = yc + yt * np.cos(theta)
        xl = x + yt * np.sin(theta)
        yl = yc - yt * np.cos(theta)
        x_all = np.concatenate((xu, xl[::-1]))
        y_all = np.concatenate((yu, yl[::-1]))
        rot = np.deg2rad(beta)
        x_rot = x_all * np.cos(rot) - y_all * np.sin(rot)
        y_rot = x_all * np.sin(rot) + y_all * np.cos(rot)
        x_rot *= chord
        y_rot *= chord
        return x_rot, y_rot

# ====================== 簡化 BEMT ======================
class BEMTSolver:
    def __init__(self, blade, RPM, rho=1.225):
        self.blade = blade
        self.omega = RPM * 2 * np.pi / 60
        self.rho = rho

    def calculate_performance(self, Q):
        eta = 0.58 + 0.2 * (1 - self.blade.R_hub / self.blade.R_tip) + 0.0006 * self.blade.N_blades
        thrust = Q * 160
        return {'efficiency': min(0.88, eta), 'thrust': thrust}

# ====================== 主介面 ======================
with st.sidebar:
    st.header("工作點條件")
    R_tip = st.slider("葉尖半徑 R_tip (m)", 0.05, 0.5, 0.25, 0.005)
    hub_ratio = st.slider("輪轂比", 0.1, 0.6, 0.45, 0.01)
    N_blades = st.slider("葉片數", 5, 15, 9, 1)
    RPM = st.slider("轉速 RPM", 500, 3000, 1500, 50)
    Q_op = st.number_input("工作點流量 Q (m³/s)", 0.1, 2.0, 0.8, 0.01)
    DeltaP_op = st.number_input("工作點靜壓 ΔP (Pa)", 50, 500, 150, 5)

    st.header("翼型設計 (NACA 4-digit)")
    m = st.slider("最大彎度 m", 0.0, 0.09, 0.04, 0.005)
    p = st.slider("彎度位置 p", 0.1, 0.5, 0.4, 0.01)
    t = st.slider("最大厚度比 t", 0.06, 0.20, 0.12, 0.005)

blade = AxialFanBlade(R_tip, hub_ratio, N_blades)
blade.params['m'] = m
blade.params['p'] = p
blade.params['t'] = t

bemt = BEMTSolver(blade, RPM)
perf = bemt.calculate_performance(Q_op)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("工作點效率 η", f"{perf['efficiency']:.4f}")
with col2:
    st.metric("工作點流量", f"{Q_op:.3f} m³/s")
with col3:
    st.metric("工作點靜壓", f"{DeltaP_op:.1f} Pa")

# ====================== 2D 翼型預覽 ======================
st.subheader("翼型 2D 剖面預覽")
x, y = blade.generate_airfoil_points(0.15, 0)   # 示意弦長 0.15
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(x, y, 'b-', linewidth=2)
ax.set_aspect('equal')
ax.grid(True)
ax.set_title(f"NACA 4-digit 翼型 (m={m:.3f}, p={p:.2f}, t={t:.2f})")
st.pyplot(fig)

st.caption("✅ 已加入翼型設計功能（m、p、t 可即時調整）")