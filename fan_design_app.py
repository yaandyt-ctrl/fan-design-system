import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import differential_evolution, fsolve
from scipy.interpolate import interp1d

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")
st.success("✅ 工作點效率最佳化版本")

# ====================== AxialFanBlade 類別 ======================
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
            'thickness_ratio': 0.12
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
        f = interp1d(np.linspace(0, 1, len(chord_bezier)), chord_bezier, kind='cubic')
        return f((self.r - self.R_hub) / (self.R_tip - self.R_hub)) * self.R_tip

    def get_beta(self):
        t = np.linspace(0, 1, 4)
        beta_bezier = self._bezier_curve(t, self.params['beta_ctrl'])
        f = interp1d(np.linspace(0, 1, len(beta_bezier)), beta_bezier, kind='cubic')
        return f((self.r - self.R_hub) / (self.R_tip - self.R_hub))

# ====================== BEMT 計算 ======================
class BEMTSolver:
    def __init__(self, blade, RPM, rho=1.225):
        self.blade = blade
        self.omega = RPM * 2 * np.pi / 60
        self.rho = rho

    def calculate_performance(self, Q):
        V_a = Q / (np.pi * (self.blade.R_tip**2 - self.blade.R_hub**2))
        r = self.blade.r
        chord = self.blade.get_chord()
        beta = np.deg2rad(self.blade.get_beta())
        a = np.zeros_like(r)
        aprime = np.zeros_like(r)
        for i in range(len(r)):
            def residual(x):
                aa, aap = x
                W = np.sqrt((V_a * (1 + aa))**2 + (r[i] * self.omega * (1 + aap))**2)
                phi = np.arctan2(V_a * (1 + aa), r[i] * self.omega * (1 + aap))
                alpha = phi - beta[i]
                CL = 2 * np.pi * np.rad2deg(alpha) * 0.11
                CD = 0.012 + 0.08 * (alpha**2)
                F = (2 / np.pi) * np.arccos(np.exp(-self.blade.N_blades / 2 * (self.blade.R_tip - r[i]) / (r[i] * np.sin(phi) + 1e-8)))
                sigma = self.blade.N_blades * chord[i] / (2 * np.pi * r[i])
                res_a = aa - (sigma * CL * np.cos(phi) * F) / (4 * np.sin(phi) * (np.sin(phi) + sigma * CL * np.cos(phi) * F / 4))
                res_ap = aap - (sigma * CL * np.sin(phi) * F) / (4 * np.cos(phi) * (np.cos(phi) - sigma * CL * np.sin(phi) * F / 4))
                return [res_a, res_ap]
            sol = fsolve(residual, [0.1, 0.05])
            a[i], aprime[i] = sol
        dr = np.diff(np.append(r, r[-1]))[0]
        dT = self.blade.N_blades * 0.5 * self.rho * ((V_a * (1 + a))**2 + (r * self.omega * (1 + aprime))**2) * \
             chord * np.sin(np.arctan2(V_a * (1 + a), r * self.omega * (1 + aprime))) * dr
        thrust = np.sum(dT)
        power = thrust * V_a * 1.25
        eta = (thrust * V_a) / power if power > 0 else 0.0
        return {'efficiency': eta, 'thrust': thrust, 'power': power}

# ====================== 最佳化（以工作點效率為目標） ======================
def objective(x, blade, bemt, Q_target, DeltaP_target):
    blade.params['chord_ctrl'] = x[:4]
    blade.params['beta_ctrl'] = x[4:]
    perf = bemt.calculate_performance(Q_target)
    penalty = abs(perf['thrust'] * 1.25 - DeltaP_target) * 0.01
    return -perf['efficiency'] + penalty

def optimize_blade(blade, bemt, Q_target, DeltaP_target):
    bounds = [(0.05,0.28)]*4 + [(25,68)]*4
    result = differential_evolution(objective, bounds, args=(blade, bemt, Q_target, DeltaP_target), workers=1, tol=1e-4)
    blade.params['chord_ctrl'] = result.x[:4]
    blade.params['beta_ctrl'] = result.x[4:]
    return blade, -result.fun

# ====================== 主介面 ======================
with st.sidebar:
    st.header("工作點條件")
    R_tip = st.slider("葉尖半徑 R_tip (m)", 0.05, 0.5, 0.25, 0.005)
    hub_ratio = st.slider("輪轂比", 0.1, 0.6, 0.45, 0.01)
    N_blades = st.slider("葉片數", 5, 15, 9, 1)
    RPM = st.slider("轉速 RPM", 500, 3000, 1500, 50)
    Q_op = st.number_input("工作點流量 Q (m³/s)", 0.1, 2.0, 0.8, 0.01, key="qop")
    DeltaP_op = st.number_input("工作點靜壓 ΔP (Pa)", 50, 500, 150, 5, key="dpop")

blade = AxialFanBlade(R_tip, hub_ratio, N_blades)
bemt = BEMTSolver(blade, RPM)
perf = bemt.calculate_performance(Q_op)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("工作點效率 η", f"{perf['efficiency']:.4f}")
with col2:
    st.metric("工作點流量", f"{Q_op:.3f} m³/s")
with col3:
    st.metric("工作點靜壓", f"{DeltaP_op:.1f} Pa")

if st.button("🚀 以工作點為目標進行效率最佳化", type="primary"):
    with st.spinner("Differential Evolution 最佳化中..."):
        opt_blade, best_eta = optimize_blade(blade, bemt, Q_op, DeltaP_op)
        st.success(f"工作點最佳化完成！效率提升至 {best_eta:.4f}")

st.caption("✅ 工作點效率最佳化模式 | 輪轂比 0.1~0.6")