import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import differential_evolution, fsolve
from scipy.interpolate import interp1d

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")
st.success("✅ 單檔案完整版已載入")

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

# ====================== 最佳化 ======================
def objective(x, blade, bemt, Q_target, DeltaP_target):
    blade.params['chord_ctrl'] = x[:4]
    blade.params['beta_ctrl'] = x[4:]
    perf = bemt.calculate_performance(Q_target)
    penalty = abs(perf['thrust'] * 1.25 - DeltaP_target) * 0.02
    return -perf['efficiency'] + penalty

def optimize_blade(blade, bemt, Q_target, DeltaP_target):
    bounds = [(0.05,0.28)]*4 + [(25,68)]*4
    result = differential_evolution(objective, bounds, args=(blade, bemt, Q_target, DeltaP_target), workers=1, tol=1e-4)
    blade.params['chord_ctrl'] = result.x[:4]
    blade.params['beta_ctrl'] = result.x[4:]
    return blade, -result.fun

# ====================== 主介面 ======================
with st.sidebar